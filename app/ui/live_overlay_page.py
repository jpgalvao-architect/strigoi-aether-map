# SPDX-License-Identifier: GPL-3.0-only
"""Live area selection is a primary workflow; file calibration remains an advanced option."""
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout
from app.ui.localized_widgets import QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QMessageBox, QSpinBox, QToolButton, QWidget

from app.infrastructure.storage import atomic_json
from app.modules.overlay.selection import CaptureArea
from app.ui.screen_selection import ScreenSelection
from app.ui.widgets import button, label, page_header, row


class LiveOverlayPage(QWidget):
    def __init__(self, context, service):
        super().__init__()
        self.context, self.service = context, service
        self.selector = None
        self.dataset_identity = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26,20,26,20)
        layout.addWidget(page_header("Overlay", "Veja os pontos do atlas sobre o mapa do jogo."))
        layout.addWidget(label("Escolha o mapa e a tela. Para usar o minimapa, selecione somente a área do terreno uma vez.", "badge", True))
        form_group = QGroupBox("Mapa e tela")
        columns=QHBoxLayout(form_group)
        form=QFormLayout()
        tuning=QFormLayout()
        columns.addLayout(form,1)
        columns.addLayout(tuning,1)
        self.maps = QComboBox()
        self.view_kind=QComboBox()
        self.view_kind.addItem("Mapa grande • monitor inteiro","large")
        self.view_kind.addItem("Minimapa + mapa grande automático","minimap")
        self.view_kind.setCurrentIndex(self.view_kind.findData(context.prefs.overlay.map_view))
        self.screens = QComboBox()
        for screen in QGuiApplication.screens():
            g=screen.geometry();ratio=screen.devicePixelRatio()
            self.screens.addItem(f"{screen.name()} • {round(g.width()*ratio)} × {round(g.height()*ratio)} pixels • {ratio*100:.0f}%", screen.name())
        from app.ui.layer_menu import AtlasLayerMenu
        self.layers = AtlasLayerMenu(context)
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(.1,1); self.opacity.setSingleStep(.1); self.opacity.setValue(context.prefs.overlay.opacity)
        self.scale = QDoubleSpinBox()
        self.scale.setRange(.5,3); self.scale.setSingleStep(.1); self.scale.setValue(context.prefs.overlay.scale)
        self.minimum = QSpinBox()
        self.minimum.setRange(12,80); self.minimum.setValue(context.prefs.overlay.minimum_matches)
        self.minimum.setToolTip("Mais detalhes correspondentes exigem evidência mais forte; podem dificultar o reconhecimento em áreas pequenas.")
        self.render_rate=QComboBox()
        for value in [60,120,240]:
            self.render_rate.addItem(f"{value} Hz • meta de desenho",value)
        self.render_rate.setCurrentIndex(self.render_rate.findData(context.prefs.overlay.render_hz))
        self.capture_rate=QSpinBox()
        self.capture_rate.setRange(10,60)
        self.capture_rate.setValue(context.prefs.overlay.capture_hz)
        self.capture_rate.setSuffix(" fps • limite")
        for index,(text, widget) in enumerate([("Modo",self.view_kind),("Mapa",self.maps),("Monitor",self.screens),("Mostrar",self.layers),("Opacidade",self.opacity),("Tamanho dos ícones",self.scale),]):
            (form if index<4 else tuning).addRow(text,widget)
        layout.addWidget(form_group)
        self.area_label = label("", "subtitle",True)
        self.status = label("Desligado", "eyebrow",True)
        layout.addWidget(self.area_label); layout.addWidget(self.status)
        self.rates=label("", "subtitle",True)
        
        self.select_button = button("Selecionar minimapa",self.select_area)
        self.start_button = button("Ativar overlay",self.start,True)
        self.stop_button=button("Desativar",self.stop)
        layout.addLayout(row(self.select_button,self.start_button,self.stop_button))
        self.events_toggle = QCheckBox("Mostrar painel de eventos")
        self.events_toggle.setChecked(context.prefs.overlay.events_panel)
        self.events_toggle.toggled.connect(self.toggle_events)
        layout.addWidget(self.events_toggle)
        layout.addWidget(label("Ao abrir o mapa grande com M, o overlay muda automaticamente. Ao fechar, volta ao minimapa.", "subtitle",True))
        self.advanced_button=QToolButton()
        self.advanced_button.setText('Ajustes avançados')
        self.advanced_button.setCheckable(True)
        self.advanced_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.advanced_button.setArrowType(Qt.ArrowType.RightArrow)
        layout.addWidget(self.advanced_button)
        self.advanced=QGroupBox('Precisão e desempenho')
        advanced_layout=QVBoxLayout(self.advanced)
        fields=QFormLayout()
        fields.addRow('Detalhes mínimos',self.minimum)
        fields.addRow('Frequência visual',self.render_rate)
        fields.addRow('Leitura do minimapa',self.capture_rate)
        advanced_layout.addLayout(fields)
        advanced_layout.addWidget(self.rates)
        advanced_layout.addWidget(button('Usar referência fixa de uma imagem',self.import_fixed))
        advanced_layout.addWidget(label('A referência fixa mantém a posição e o zoom calibrados. Use apenas se precisar de uma calibração manual.','subtitle',True))
        self.advanced.setVisible(False)
        layout.addWidget(self.advanced)
        self.advanced_button.toggled.connect(self.show_advanced)
        layout.addStretch()
        service.status_changed.connect(self.status.setText)
        context.changed.connect(self.refresh)
        self.refresh()
        for widget in [self.opacity,self.scale]:
            widget.valueChanged.connect(self.save_fields)
        self.render_rate.currentIndexChanged.connect(self.save_fields)
        self.view_kind.currentIndexChanged.connect(self.change_view)
        self.rate_timer=QTimer(self)
        self.rate_timer.setInterval(1000)
        self.rate_timer.timeout.connect(self.refresh_rates)
        self.rate_timer.start()
        self.refresh_rates()

    def refresh(self):
        if self.dataset_identity is not self.context.dataset:
            self.maps.clear()
            for m in self.context.dataset.maps:
                self.maps.addItem(m.name.removesuffix(' • base compartilhada'),m.id)
            self.maps.setCurrentIndex(max(0,self.maps.findData(self.context.prefs.overlay.map_id)))
            self.dataset_identity = self.context.dataset
        active = self.context.prefs.overlay.enabled or self.selector is not None
        for widget in [self.maps,self.screens,self.minimum,self.view_kind,self.capture_rate,self.start_button]:
            widget.setEnabled(not active)
        self.stop_button.setEnabled(self.context.prefs.overlay.enabled)
        mini=self.view_kind.currentData()=="minimap"
        self.select_button.setVisible(mini)
        self.select_button.setEnabled(not active and mini)
        self.capture_rate.setEnabled(not active and mini)
        path = self.context.prefs.overlay.minimap_area if mini else self.context.prefs.overlay.capture_area
        if path and Path(path).is_file():
            try:
                from app.infrastructure.storage import load_model
                area = load_model(Path(path),CaptureArea)
                r=area.pixel_ratio
                width=round((area.x+area.width)*r)-round(area.x*r)
                height=round((area.y+area.height)*r)-round(area.y*r)
                self.area_label.setText(f"Minimapa selecionado · {width} × {height} pixels")
                self.area_label.setToolTip(f"{area.screen_name} · escala {r*100:.0f}% · {area.map_id}")
            except (ValueError,OSError):
                self.area_label.setText("A seleção anterior precisa ser refeita.")
        else:
            self.area_label.setText("Selecione o terreno do minimapa, sem a barra de título." if mini else "Mapa grande pronto. Não é preciso selecionar uma área.")
        self.events_toggle.blockSignals(True)
        self.events_toggle.setChecked(self.context.prefs.overlay.events_panel)
        self.events_toggle.blockSignals(False)

    def show_advanced(self,checked):
        from PySide6.QtCore import Qt
        self.advanced.setVisible(checked)
        self.advanced_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)

    def change_view(self):
        self.context.prefs.overlay.map_view=self.view_kind.currentData()
        self.context.save()

    def refresh_rates(self):
        prefs=self.context.prefs.overlay
        self.rates.setText(f"Desenho: meta {prefs.render_hz} Hz • medido {self.service.window.paint_hz:.0f} Hz\nRastreamento visual: {self.service.observation_hz:.0f} atualizações/s • revalidação do mapa separada. A taxa real depende do sistema e do monitor.")

    def save_fields(self):
        prefs = self.context.prefs.overlay
        prefs.map_id = self.maps.currentData()
        prefs.layers = "atlas"
        prefs.opacity = self.opacity.value()
        prefs.scale = self.scale.value()
        prefs.minimum_matches = self.minimum.value()
        prefs.map_view=self.view_kind.currentData()
        prefs.render_hz=self.render_rate.currentData()
        prefs.capture_hz=self.capture_rate.value()
        self.context.save()

    def select_area(self):
        self.service.stop()
        self.save_fields()
        screens = [s for s in QGuiApplication.screens() if s.name()==self.screens.currentData()]
        if len(screens)!=1:
            self.status.setText("Monitor indisponível. Reabra o app após conectar a tela.")
            return
        self.screen = screens[0]
        self.main_window = self.window()
        self.was_visible = self.main_window.isVisible()
        self.main_window.hide()
        self.status.setText("Selecione a área do mapa na tela…")
        # Allow the app window to disappear before displaying the transparent selector.
        QTimer.singleShot(200,self.show_selector)

    def show_selector(self):
        self.selector = ScreenSelection(self.screen)
        self.selector.chosen.connect(self.accept_area)
        self.selector.cancelled.connect(self.cancel_area)
        self.selector.show()
        self.selector.activateWindow()
        self.refresh()

    def finish_selection(self):
        if self.selector:
            self.selector.deleteLater()
            self.selector = None
        if self.was_visible:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
        self.refresh()

    def accept_area(self, rectangle):
        try:
            geometry = self.screen.geometry()
            area = CaptureArea(map_id=self.maps.currentData(),screen_name=self.screen.name(),
                screen_x=geometry.x(),screen_y=geometry.y(),screen_width=geometry.width(),screen_height=geometry.height(),
                pixel_ratio=self.screen.devicePixelRatio(),x=rectangle.x(),y=rectangle.y(),width=rectangle.width(),height=rectangle.height(),view_kind=self.view_kind.currentData())
            path = self.context.directory/'calibration'/f'area-{uuid4().hex}.json'
            atomic_json(path,area)
            if area.view_kind=="minimap":
                self.context.prefs.overlay.minimap_area=str(path)
            else:
                self.context.prefs.overlay.capture_area = str(path)
            self.context.prefs.overlay.tracking_mode = "dynamic"
            self.context.save()
            self.status.setText("Área salva. Ative o overlay com o mapa aberto.")
        except (ValueError,OSError) as exc:
            self.status.setText(str(exc))
        finally:
            self.finish_selection()

    def cancel_area(self):
        self.status.setText("Seleção cancelada; área anterior preservada.")
        self.finish_selection()

    def start(self):
        try:
            self.save_fields()
            if self.context.prefs.overlay.map_view=="large":
                screens=[s for s in QGuiApplication.screens() if s.name()==self.screens.currentData()]
                if len(screens)!=1:
                    raise ValueError("Monitor indisponível")
                screen=screens[0];g=screen.geometry()
                area=CaptureArea(map_id=self.maps.currentData(),screen_name=screen.name(),screen_x=g.x(),screen_y=g.y(),
                    screen_width=g.width(),screen_height=g.height(),pixel_ratio=screen.devicePixelRatio(),
                    x=0,y=0,width=g.width(),height=g.height(),view_kind="large")
                path=self.context.directory/'calibration'/'large-screen.json'
                atomic_json(path,area)
                self.context.prefs.overlay.capture_area=str(path)
            self.context.prefs.overlay.tracking_mode = "dynamic"
            self.service.start()
            # Minimize the companion so it does not cover the game area being recognized.
            self.window().showMinimized()
        except Exception as exc:
            self.status.setText(str(exc))

    def stop(self):
        self.service.stop()
        self.context.save()

    def toggle_events(self, enabled):
        self.context.prefs.overlay.events_panel = enabled
        self.context.save()

    def import_fixed(self):
        from app.ui.calibration_dialog import CalibrationDialog
        filename,_ = QFileDialog.getOpenFileName(self,"Imagem existente","","Imagens (*.png *.jpg *.jpeg)")
        if not filename:
            return
        try:
            self.save_fields()
            dialog = CalibrationDialog(Path(filename),self.maps.currentData(),self.context.directory,self)
            if dialog.exec()==QDialog.DialogCode.Accepted:
                self.context.prefs.overlay.calibration = dialog.result_path
                self.context.prefs.overlay.tracking_mode = "fixed"
                self.context.save()
                self.service.start()
        except Exception as exc:
            QMessageBox.warning(self,"Referência fixa indisponível",str(exc))

    def shutdown(self):
        self.rate_timer.stop()
        if self.selector:
            self.was_visible = False
            self.selector.close()
