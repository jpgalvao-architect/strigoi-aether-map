# SPDX-License-Identifier: GPL-3.0-only
"""Map-first route planning, editing and reuse with automatic minimap-center tracking."""
from pathlib import Path
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QVBoxLayout,QHBoxLayout,QListWidget,QListWidgetItem,QSlider,QInputDialog,QScrollArea,QSizePolicy)
from app.ui.localized_widgets import QWidget,QFrame,QDialog,QLineEdit,QComboBox,QCheckBox,QPushButton,QFileDialog,QMessageBox,QToolButton
from app.ui.widgets import label,button,row
from app.ui.icons import icon
from app.core.i18n import tr
from app.modules.routes.models import Vertex
from app.modules.routes.planner import candidates,rebuild,distance
from app.ui.route_view import RouteView


class RoutesPage(QWidget):
    def heightForWidth(self,width):
        # The map expands to available height; wrapped side options scroll locally.
        return self.minimumSizeHint().height()

    def __init__(self,context,service,start_overlay=None,overlay=None):
        super().__init__();self.context=context;self.service=service;self.start_overlay=start_overlay;self.overlay=overlay
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Ignored)
        self.resources=[];self.mode='loop';self.edit_mode='';self.history=[];self._refreshing=False
        self._shown_draft=None
        layout=QVBoxLayout(self);layout.setContentsMargins(26,20,26,20);layout.setSpacing(15)
        head=QVBoxLayout();head.setSpacing(4);head.addWidget(label('EXPLORE COM UM PLANO','eyebrow'))
        head.addWidget(label('Rotas de farm','title'));head.addWidget(label('Escolha o que procurar. O próximo trecho vai com você.','subtitle'))
        top=QHBoxLayout();top.addLayout(head,1);top.addWidget(button('Minhas rotas',self.saved_routes));layout.addLayout(top)
        body=QHBoxLayout();body.setSpacing(20);layout.addLayout(body,1)
        left=QVBoxLayout();left.setSpacing(9);body.addLayout(left,1)
        self.maps=QComboBox()
        for m in context.atlas_dataset.maps:self.maps.addItem(m.name.split(' • ')[0].split(' · ')[0],m.id)
        self.maps.setCurrentIndex(max(0,self.maps.findData(context.prefs.map_id)))
        self.source=label('Base comunitária','subtitle');self.source.setToolTip('Locais cadastrados no Atlas; presença e passagens precisam ser conferidas no jogo.')
        left.addLayout(row(self.maps,self.source))
        self.view=RouteView();left.addWidget(self.view,1)
        self.map_hint=label('Tracejado: ligação sugerida · contínuo: passagem conferida por você.','subtitle',True);left.addWidget(self.map_hint)
        self.origin_button=button('Marcar início',lambda:self.set_edit('origin'))
        left.addLayout(row(self.origin_button,button('−',lambda:self.view.zoom(-1)),button('+',lambda:self.view.zoom(1)),button('Enquadrar rota',lambda:self.view.fit_route(self.service.draft))))
        side=QFrame();side.setObjectName('routeSetup');side.setFixedWidth(266)
        side.setStyleSheet('QFrame#routeSetup{border:0;border-left:1px solid #34303f;background:transparent;}')
        form=QVBoxLayout(side);form.setContentsMargins(18,0,12,0);form.setSpacing(10)
        side_scroll=QScrollArea();side_scroll.setWidgetResizable(True);side_scroll.setFrameShape(QFrame.NoFrame)
        side_scroll.setFixedWidth(282);side_scroll.setWidget(side);side_scroll.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Ignored)
        body.addWidget(side_scroll)
        form.addWidget(label('O QUE VAMOS PROCURAR?','eyebrow'))
        self.targets=button('Escolher alvos',self.choose_targets);self.targets.setIcon(icon('gatherables'));form.addWidget(self.targets)
        self.count=label('','subtitle',True);form.addWidget(self.count)
        form.addWidget(label('Percurso','subtitle'))
        self.loop=button('Circuito',lambda:self.change_mode('loop'));self.open=button('Só ida',lambda:self.change_mode('open'))
        for b in (self.loop,self.open):b.setCheckable(True)
        form.addLayout(row(self.loop,self.open))
        form.addLayout(row(label('Paradas','subtitle'),label('')))
        self.limit_label=label('12','sectionTitle');form.addWidget(self.limit_label)
        self.limit=QSlider(Qt.Horizontal);self.limit.setRange(2,60);self.limit.setValue(12)
        self.limit.setAccessibleName(tr('Quantidade de paradas'));form.addWidget(self.limit)
        self.title=label('','sectionTitle',True);self.title.setTextFormat(Qt.PlainText);form.addWidget(self.title)
        self.summary=label('','subtitle',True);form.addWidget(self.summary)
        self.start_button=button('Iniciar no minimapa',self.start);self.start_button.setObjectName('primary');self.start_button.setIcon(icon('chevron-right'));form.addWidget(self.start_button)
        form.addLayout(row(button('Salvar',self.save),button('Renomear',self.rename)))
        self.edit_button=button('Ajustar trajeto',lambda:self.set_edit('passage'));form.addWidget(self.edit_button)
        self.undo=button('Desfazer ajuste',self.undo_edit);form.addWidget(self.undo)
        form.addWidget(button('Marcar meus pontos',lambda:self.set_edit('custom')))
        self.review=QCheckBox('Conferi as passagens ajustadas');self.review.toggled.connect(self.review_passages);form.addWidget(self.review)
        self.advanced_toggle=QToolButton();self.advanced_toggle.setText('Acompanhamento e percurso');self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);self.advanced_toggle.setArrowType(Qt.RightArrow)
        self.advanced_toggle.setStyleSheet('QToolButton{border:0;background:transparent;color:#aaa8bd;padding:5px 0;}')
        form.addWidget(self.advanced_toggle)
        self.advanced=QWidget();advanced=QVBoxLayout(self.advanced);advanced.setContentsMargins(0,0,0,0);advanced.setSpacing(8)
        self.auto=QCheckBox('Avançar ao visitar a parada');self.auto.setChecked(context.prefs.routes.auto_advance)
        self.auto.toggled.connect(self.auto_changed);advanced.addWidget(self.auto)
        advanced.addWidget(button('Inverter sentido',service.reverse))
        self.record=QCheckBox('Gravar meu percurso');self.record.toggled.connect(service.set_recording);advanced.addWidget(self.record)
        self.use_recorded=button('Revisar percurso registrado',self.review_recorded);advanced.addWidget(self.use_recorded)
        self.advanced.hide();self.advanced_toggle.toggled.connect(self.advanced.setVisible);form.addWidget(self.advanced)
        self.advanced_toggle.toggled.connect(lambda checked:self.advanced_toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow))
        self.note=label('Os locais vêm do Atlas. As passagens entre eles precisam ser conferidas.','subtitle',True);form.addWidget(self.note)
        form.addStretch()
        self.status=label('','subtitle',True);layout.addWidget(self.status)
        self.debounce=QTimer(self);self.debounce.setSingleShot(True);self.debounce.setInterval(180);self.debounce.timeout.connect(self.generate)
        self.limit.valueChanged.connect(lambda *_:self.debounce.start())
        self.maps.currentIndexChanged.connect(self.map_changed)
        self.view.map_clicked.connect(self.map_clicked)
        service.changed.connect(self.refresh)
        self.map_changed()

    def map_changed(self):
        if self._refreshing:return
        dataset=self.service.dataset;map_id=self.maps.currentData()
        definition=next((m for m in dataset.maps if m.id==map_id),None)
        if not definition:return
        self.view.set_map(definition)
        available={p.resource_id for p in dataset.all_points if p.map_id==map_id and p.enabled}
        self.resources=[r for r in self.resources if r in available]
        if not self.resources:self.resources=['azpha'] if 'azpha' in available else sorted(available)[:1]
        self.generate()

    def generate(self,start=None):
        self.debounce.stop()
        self.limit.blockSignals(True);self.limit.setMinimum(max(2,len(self.resources)));self.limit.blockSignals(False)
        try:
            self.history=[];self.service.plan(self.maps.currentData(),self.resources,self.limit.value(),self.mode,start)
            self._shown_draft=self.service.draft;self.view.fit_route(self.service.draft)
        except ValueError as exc:
            self.service.draft=None;self.refresh();self.status.setText(str(exc))

    def change_mode(self,mode):
        self.mode=mode
        if self.service.draft and not self.resources:
            changed=self.service.draft.model_copy(update={'mode':mode},deep=True)
            self.service.draft=rebuild(changed);self.refresh()
        else:self.generate()

    def choose_targets(self):
        dialog=QDialog(self);dialog.setWindowTitle('Escolha o que procurar');dialog.resize(430,510)
        box=QVBoxLayout(dialog);search=QLineEdit();search.setPlaceholderText('Buscar recurso, pet ou cubo…');box.addWidget(search)
        listing=QListWidget();box.addWidget(listing,1)
        dataset=self.service.dataset;counts={}
        for p in dataset.all_points:
            if p.map_id==self.maps.currentData() and p.enabled:counts[p.resource_id]=counts.get(p.resource_id,0)+1
        for resource in sorted(dataset.resources,key=lambda r:r.name):
            if counts.get(resource.id,0)<1:continue
            item=QListWidgetItem(resource.name+f' · {counts[resource.id]} '+tr('locais'),listing)
            item.setData(Qt.UserRole,resource.id);item.setToolTip(resource.verification)
            item.setFlags(item.flags()|Qt.ItemIsUserCheckable);item.setCheckState(Qt.Checked if resource.id in self.resources else Qt.Unchecked)
        search.textChanged.connect(lambda text:[listing.item(i).setHidden(text.casefold() not in listing.item(i).text().casefold()) for i in range(listing.count())])
        def accept():
            selected=[listing.item(i).data(Qt.UserRole) for i in range(listing.count()) if listing.item(i).checkState()==Qt.Checked]
            if not selected or len(selected)>32:return
            self.resources=selected;dialog.accept();self.generate()
        use=button('Usar seleção',accept)
        def selection_changed():
            count=sum(listing.item(i).checkState()==Qt.Checked for i in range(listing.count()))
            use.setEnabled(1<=count<=32)
        listing.itemChanged.connect(selection_changed);selection_changed()
        box.addWidget(use);box.addWidget(button('Cancelar',dialog.reject));dialog.exec()

    def refresh(self):
        if self._refreshing:return
        self._refreshing=True
        try:
            route=self.service.draft;names={r.id:r.name for r in self.service.dataset.resources}
            text=' + '.join(names.get(r,r) for r in self.resources) or tr('Meus pontos')
            self.targets.setText(self.targets.fontMetrics().elidedText(text,Qt.ElideRight,max(170,self.targets.width()-44)))
            self.targets.setToolTip(text)
            self.count.setText(tr('{count} locais cadastrados neste mapa.').format(count=len(candidates(self.service.dataset,self.maps.currentData(),self.resources))))
            self.limit_label.setText(str(self.limit.value()));self.loop.setChecked(self.mode=='loop');self.open.setChecked(self.mode=='open')
            self.limit.setEnabled(bool(self.resources))
            self.view.show_route(route)
            self.title.setText(route.name if route else 'Escolha pelo menos dois locais.')
            self.summary.setText(tr('{count} paradas · {mode}').format(count=len(route.stops),mode=tr('volta ao início' if route.mode=='loop' else 'termina no último ponto')) if route else '')
            self.start_button.setEnabled(route is not None);self.edit_button.setEnabled(route is not None)
            self.undo.setVisible(bool(self.history))
            self.review.blockSignals(True);adjusted=[l for l in route.legs if l.origin!='suggested'] if route else []
            self.review.setEnabled(bool(adjusted));self.review.setChecked(bool(adjusted) and all(l.reviewed for l in adjusted));self.review.blockSignals(False)
            self.record.blockSignals(True);self.record.setChecked(self.service.recording);self.record.blockSignals(False)
            self.record.setEnabled(self.service.active and not self.service.complete)
            self.use_recorded.setEnabled(bool(self.service.recordings))
            self.status.setText(self.service.status)
        finally:self._refreshing=False

    def set_edit(self,mode):
        self.edit_mode='' if self.edit_mode==mode else mode;self.view.editing=bool(self.edit_mode)
        if self.edit_mode=='custom':
            self.remember();self.resources=[];self.debounce.stop();self.service.draft=None;self.service._custom_first=None
            self.service.notify('Marque locais próprios. São necessários pelo menos dois.')
        self.map_hint.setText({'origin':'Clique na parada por onde quer começar.','passage':'Clique no mapa para inserir uma passagem.','custom':'Marque locais próprios. São necessários pelo menos dois.'}.get(self.edit_mode,'Tracejado: ligação sugerida · contínuo: passagem conferida por você.'))

    def remember(self):
        if self.service.draft:self.history=(self.history+[self.service.draft.model_copy(deep=True)])[-20:]

    def map_clicked(self,x,y):
        point=Vertex(x=x,y=y);draft=self.service.draft
        if self.edit_mode=='custom':
            self.remember()
            try:self.service.custom_pair(self.maps.currentData(),point,self.mode)
            except ValueError as exc:self.status.setText(str(exc))
        elif self.edit_mode=='origin' and draft:
            self.remember();index=min(range(len(draft.stops)),key=lambda i:distance(draft.stops[i],point))
            changed=draft.model_copy(deep=True,update={'stops':draft.stops[index:]+draft.stops[:index]})
            self.service.draft=rebuild(changed,library=self.service.library.routes);self.set_edit('origin');self.service.changed.emit()
        elif self.edit_mode=='passage' and draft:
            self.remember()
            index=min(range(len(draft.legs)),key=lambda i:min(self.segment_distance(point,a,b) for a,b in zip(draft.legs[i].vertices,draft.legs[i].vertices[1:])))
            try:self.service.edit_passage(index,point)
            except ValueError as exc:self.status.setText(str(exc))

    @staticmethod
    def segment_distance(p,a,b):
        dx,dy=b.x-a.x,b.y-a.y;t=max(0,min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/(dx*dx+dy*dy))) if dx or dy else 0
        return ((p.x-a.x-t*dx)**2+(p.y-a.y-t*dy)**2)**.5

    def undo_edit(self):
        if self.history:
            self.service.draft=self.history.pop();self.resources=self.service.draft.resources[:];self.mode=self.service.draft.mode
            self.service.changed.emit()

    def review_passages(self,checked):
        if self._refreshing:return
        if self.service.draft:
            for leg in self.service.draft.legs:
                if leg.origin!='suggested':leg.reviewed=checked
            self.service.changed.emit()

    def auto_changed(self,checked):self.context.prefs.routes.auto_advance=checked;self.context.save()

    def start(self):
        try:
            self.debounce.stop();self.service.start()
            self.context.prefs.routes.panel_visible=True;self.context.save()
            if self.start_overlay:self.start_overlay()
        except (ValueError,OSError) as exc:self.status.setText(str(exc))

    def save(self):
        try:self.service.save()
        except (ValueError,OSError) as exc:self.status.setText(str(exc))

    def rename(self):
        if not self.service.draft:return
        value,ok=QInputDialog.getText(self,tr('Renomear rota'),tr('Nome da rota'),text=self.service.draft.name)
        if ok and value.strip():self.service.draft.name=value.strip()[:180];self.refresh()

    def saved_routes(self):
        dialog=QDialog(self);dialog.setWindowTitle('Minhas rotas');dialog.resize(500,440)
        box=QVBoxLayout(dialog);listing=QListWidget();box.addWidget(listing,1)
        def populate():
            listing.clear()
            for route in self.service.library.routes:
                item=QListWidgetItem(route.name+' · '+route.map_id+f' · {len(route.stops)} '+tr('paradas'),listing);item.setData(Qt.UserRole,route.id)
        def load():
            item=listing.currentItem()
            if not item:return
            try:
                self.service.load(item.data(Qt.UserRole));self.display_draft();dialog.accept()
            except (ValueError,OSError) as exc:QMessageBox.warning(dialog,'Rota indisponível',str(exc))
        def delete():
            item=listing.currentItem()
            if item and QMessageBox.question(dialog,'Excluir rota','Excluir somente esta rota salva?')==QMessageBox.Yes:
                self.service.delete(item.data(Qt.UserRole));populate()
        box.addLayout(row(button('Carregar',load),button('Excluir',delete),button('Importar',lambda:self.transfer(True,populate)),button('Exportar',lambda:self.transfer(False,populate))))
        box.addWidget(button('Fechar',dialog.accept));populate();dialog.exec()

    def transfer(self,importing,callback):
        chooser=QFileDialog.getOpenFileName if importing else QFileDialog.getSaveFileName
        name,_=chooser(self,'Importar rotas' if importing else 'Exportar rotas','','JSON (*.json)')
        if not name:return
        try:
            self.service.import_file(Path(name)) if importing else self.service.export_file(Path(name));callback()
        except (OSError,ValueError) as exc:QMessageBox.warning(self,'Rotas',str(exc))

    def review_recorded(self):
        try:self.service.use_recorded();self.display_draft()
        except ValueError as exc:self.status.setText(str(exc))

    def display_draft(self):
        route=self.service.draft;self.debounce.stop();self.history=[];self.edit_mode='';self.view.editing=False
        self.maps.blockSignals(True);self.maps.setCurrentIndex(self.maps.findData(route.map_id));self.maps.blockSignals(False)
        definition=next(m for m in self.service.dataset.maps if m.id==route.map_id);self.view.set_map(definition)
        self.resources=route.resources[:];self.mode=route.mode
        self.limit.blockSignals(True);self.limit.setMinimum(max(2,len(self.resources)));self.limit.setValue(len(route.stops));self.limit.blockSignals(False)
        self.map_hint.setText('Tracejado: ligação sugerida · contínuo: passagem conferida por você.')
        self.refresh();self.view.fit_route(route)

    def choose_resource(self,map_id,resource_id):
        self.maps.blockSignals(True);self.maps.setCurrentIndex(self.maps.findData(map_id));self.maps.blockSignals(False)
        self.resources=[resource_id];self.map_changed()

    def shutdown(self):self.debounce.stop()
