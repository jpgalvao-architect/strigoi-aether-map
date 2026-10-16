# SPDX-License-Identifier: GPL-3.0-only
"""Panorama of real character records; missing readings never become zero."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout,QHBoxLayout,QGridLayout
from app.core.i18n import calendar_date,clock,language,tr
from app.modules.routine.models import RESOURCES
from app.ui.localized_widgets import QWidget,QFrame,QToolButton,QCheckBox,QComboBox,QDialog,QFormLayout,QDoubleSpinBox
from app.ui.widgets import label,button
from app.ui.combat_classes import colored_class_icon,class_label
from app.ui.icons import icon
from app.ui.identity import emblem_icon


def reading_stamp(profile):
    stamps=[reading.observed_at for reading in profile.counters.values()]
    if not stamps:return ''
    stamp=max(stamps).astimezone()
    return calendar_date(stamp)+' · '+clock(stamp)


class RoutinePage(QWidget):
    def __init__(self,context,service):
        super().__init__()
        self.context,self.service=context,service
        self.detail_key=None;self.structure=None;self.panel=None
        self.setObjectName('routinePage')
        self.setStyleSheet('''
            QFrame#routineCard{background:#171721;border:1px solid #30303e;border-radius:7px;}
            QFrame#routineCell{border:0;border-top:1px solid #30303e;background:transparent;}
            QFrame#routineOpportunity{background:#211e28;border:1px solid #42394d;border-radius:7px;}
            QLabel#routineName{font-size:16px;font-weight:600;}
            QLabel#routineBalance{font-size:29px;font-weight:600;color:#e5c48b;}
            QLabel#routineCount{font-size:25px;font-weight:600;color:#c2b2fc;}
            QLabel#routineState{font-size:11px;color:#aaa8bd;}
            QToolButton#routinePin{border:0;background:transparent;padding:5px;color:#aaa8bd;}
            QToolButton#routinePin:checked{background:#302943;}
        ''')
        self.layout=QVBoxLayout(self);self.layout.setContentsMargins(30,25,30,25);self.layout.setSpacing(22)
        context.changed.connect(self.refresh);service.changed.connect(self.refresh)
        service.status_changed.connect(self.update_status)
        self.status=None
        self.refresh()

    def clear(self):
        while self.layout.count():
            item=self.layout.takeAt(0)
            widget=item.widget()
            if widget:widget.hide();widget.setParent(None);widget.deleteLater()
        self.status=None

    def refresh(self,*_):
        signature=(self.service.store.collection.model_dump_json(),self.service.profile_key,self.service.fresh,
                   self.detail_key,self.context.prefs.routine.model_dump_json(),language())
        if self.structure==signature:self.update_status();return
        self.structure=signature;self.clear()
        header=QWidget();top=QHBoxLayout(header);top.setContentsMargins(0,0,0,0);top.setSpacing(18)
        copy=QVBoxLayout();copy.setSpacing(7)
        copy.addWidget(label('ROTINA / PERSONAGENS','eyebrow'))
        copy.addWidget(label('Cada personagem, no seu ritmo.','title',True))
        copy.addWidget(label('Seus recursos, sem mais uma checklist manual.','subtitle',True))
        top.addLayout(copy,1)
        settings=QToolButton();settings.setIcon(icon('settings'));settings.setFixedSize(34,34)
        settings.setToolTip('Personalizar Rotina');settings.setAccessibleName('Personalizar Rotina')
        settings.clicked.connect(self.settings);top.addWidget(settings,0,Qt.AlignmentFlag.AlignTop)
        self.layout.addWidget(header)
        profiles=self.service.store.collection.profiles
        if self.detail_key not in profiles:self.detail_key=None
        if self.detail_key:self.details(profiles[self.detail_key])
        elif profiles:self.panorama()
        else:self.empty()
        footer=QWidget();bottom=QHBoxLayout(footer);bottom.setContentsMargins(0,0,0,0)
        self.status=label(self.service.status,'routineState',True);bottom.addWidget(self.status,1)
        self.overlay=QCheckBox('Mostrar overlay da Rotina')
        self.overlay.setChecked(self.context.prefs.routine.panel_visible)
        self.overlay.toggled.connect(self.toggle_panel);bottom.addWidget(self.overlay)
        self.layout.addWidget(footer)
        self.layout.addWidget(label('Registros separados por personagem e servidor. Dados ausentes não são tratados como zero.','routineState',True))
        self.layout.addStretch()

    def update_status(self,*_):
        if self.status:self.status.setText(self.service.status)

    def empty(self):
        surface=QFrame();surface.setObjectName('routineOpportunity')
        box=QVBoxLayout(surface);box.setContentsMargins(28,32,28,32);box.setSpacing(15)
        picture=label('');picture.setPixmap(emblem_icon().pixmap(68,68));box.addWidget(picture)
        box.addWidget(label('Uma conta. Várias aventuras.','routineName'))
        box.addWidget(label('Entre com seu personagem. A Rotina guarda as leituras recebidas e organiza seus recursos aqui.','subtitle',True))
        box.addWidget(label('Se o app foi aberto depois do personagem, entre novamente para receber o saldo inicial.','subtitle',True))
        if not self.context.prefs.routine.auto_capture:
            box.addWidget(button('Ativar sincronização automática',self.enable_capture,True))
        box.addWidget(button('Como funciona a leitura',self.how))
        self.layout.addWidget(surface)

    def panorama(self):
        profiles=self.service.store.collection.profiles
        intro=QWidget();line=QHBoxLayout(intro);line.setContentsMargins(0,0,0,0)
        copy=QVBoxLayout();copy.setSpacing(5)
        copy.addWidget(label('Seu próximo passo, em um olhar.','routineName'))
        copy.addWidget(label('Consulte a última leitura de cada personagem.','subtitle',True));line.addLayout(copy,1)
        total=sum(bool(p.counters) for p in profiles.values())
        summary=QVBoxLayout();summary.setSpacing(0)
        summary.addWidget(label(str(total),'routineCount'))
        summary.addWidget(label(tr('de {total} personagens lidos').format(total=len(profiles)),'routineState'))
        line.addLayout(summary);self.layout.addWidget(intro)
        grid_widget=QWidget();grid=QGridLayout(grid_widget);grid.setContentsMargins(0,0,0,0);grid.setSpacing(12)
        ordered=sorted(profiles.items(),key=lambda pair:(pair[0]!=self.service.profile_key,pair[1].character.casefold(),pair[1].server))
        columns=3
        for index,(key,profile) in enumerate(ordered):
            grid.addWidget(self.profile_card(key,profile),index//columns,index%columns)
        for column in range(columns):grid.setColumnStretch(column,1)
        self.layout.addWidget(grid_widget)
        note=QFrame();note.setObjectName('routineOpportunity')
        box=QHBoxLayout(note);box.setContentsMargins(18,16,18,16);box.setSpacing(16)
        copy=QVBoxLayout();copy.setSpacing(5)
        copy.addWidget(label('Acompanhe só o que faz diferença para você.','sectionTitle',True))
        copy.addWidget(label('Fixe seus recursos e escolha entre Pulso compacto e Faixa.','subtitle',True));box.addLayout(copy,1)
        box.addWidget(button('Personalizar overlay',self.settings));self.layout.addWidget(note)

    def profile_card(self,key,profile):
        frame=QFrame();frame.setObjectName('routineCard');frame.setMinimumWidth(205)
        box=QVBoxLayout(frame);box.setContentsMargins(0,0,0,0);box.setSpacing(0)
        header=QWidget();header.setFixedHeight(128)
        line=QHBoxLayout(header);line.setContentsMargins(15,17,15,17);line.setSpacing(10)
        picture=label('');picture.setPixmap(colored_class_icon(profile.job).pixmap(31,34));line.addWidget(picture)
        copy=QVBoxLayout();copy.setSpacing(4)
        name=label(profile.character,'routineName',True);copy.addWidget(name)
        copy.addWidget(label(class_label(profile.job),'routineState'))
        copy.addWidget(label(tr('Servidor {servidor}').format(servidor=profile.server)+' · '+profile.region.upper(),'routineState'))
        copy.addWidget(label(self.service.profile_status(key),'routineState'));line.addLayout(copy,1)
        box.addWidget(header)
        for resource in RESOURCES:box.addWidget(self.resource_cell(key,resource))
        stamp=reading_stamp(profile)
        updated=label(tr('Última leitura · {horario}').format(horario=stamp) if stamp else '', 'routineState')
        updated.setFixedHeight(35);updated.setContentsMargins(15,6,15,5);box.addWidget(updated)
        open_button=button('Ver rotina',lambda _,k=key:self.open_detail(k));open_button.setObjectName('quiet')
        footer=QWidget();bottom=QHBoxLayout(footer);bottom.setContentsMargins(15,0,15,8)
        bottom.addWidget(open_button);box.addWidget(footer)
        return frame

    def resource_cell(self,key,resource,detail=False):
        frame=QFrame();frame.setObjectName('routineCell')
        if not detail:frame.setFixedHeight(112)
        box=QVBoxLayout(frame);box.setContentsMargins(16,16,16,17);box.setSpacing(8)
        top=QHBoxLayout();picture=label('');picture.setPixmap(icon('energy').pixmap(15,15));top.addWidget(picture)
        top.addWidget(label(RESOURCES[resource][0],'routineState',True),1)
        if detail:
            pin=QToolButton();pin.setObjectName('routinePin');pin.setIcon(icon('routine'))
            pin.setCheckable(True);pin.setChecked(resource in self.context.prefs.routine.pinned)
            pin.setToolTip('Acompanhar no overlay');pin.setAccessibleName(tr('Acompanhar {recurso} no overlay').format(recurso=tr(RESOURCES[resource][0])))
            pin.toggled.connect(lambda enabled,r=resource:self.toggle_pin(r,enabled));top.addWidget(pin)
        box.addLayout(top)
        reading=self.service.store.reading(key,resource)
        value=label(str(reading.value) if reading else '—','routineBalance');box.addWidget(value)
        if reading is None:value.setStyleSheet('color:#aaa8bd;')
        box.addWidget(label(self.service.profile_status(key) if reading else 'Aguardando leitura','routineState'))
        if detail:
            box.addWidget(label('Saldo recebido do jogo. Limite e reposição ainda não informados.','subtitle',True))
        return frame

    def details(self,profile):
        back=button('Todos os personagens',lambda:self.open_detail(None));back.setObjectName('quiet')
        self.layout.addWidget(back)
        title=QWidget();row=QHBoxLayout(title);row.setContentsMargins(0,0,0,0);row.setSpacing(12)
        picture=label('');picture.setPixmap(colored_class_icon(profile.job).pixmap(36,40));row.addWidget(picture)
        copy=QVBoxLayout();copy.setSpacing(3)
        copy.addWidget(label(profile.character,'routineName'))
        copy.addWidget(label(tr('Servidor {servidor}').format(servidor=profile.server)+' · '+tr(self.service.profile_status(self.detail_key)),'subtitle'))
        row.addLayout(copy,1);self.layout.addWidget(title)
        values=QWidget();line=QHBoxLayout(values);line.setContentsMargins(0,0,0,0);line.setSpacing(14)
        for resource in RESOURCES:
            cell=self.resource_cell(self.detail_key,resource,True);cell.setObjectName('routineCard');line.addWidget(cell,1)
        self.layout.addWidget(values)
        self.layout.addWidget(label('O overlay acompanha o personagem em jogo. Consultar um registro salvo não troca o personagem medido.','subtitle',True))
        self.layout.addWidget(button('Como funciona a leitura',self.how))

    def open_detail(self,key):
        self.detail_key=key;self.refresh()

    def toggle_pin(self,resource,enabled):
        pins=self.context.prefs.routine.pinned
        self.context.prefs.routine.pinned=[r for r in pins if r!=resource]+([resource] if enabled else [])
        self.context.save()

    def toggle_panel(self,enabled):
        self.context.prefs.routine.panel_visible=enabled;self.context.save()

    def enable_capture(self):
        self.context.prefs.routine.auto_capture=True;self.context.save()

    def settings(self):
        dialog=QDialog(self);dialog.setWindowTitle('Personalizar Rotina');dialog.setMinimumWidth(430)
        form=QFormLayout(dialog)
        automatic=QCheckBox('Sincronizar automaticamente com o jogo')
        automatic.setChecked(self.context.prefs.routine.auto_capture)
        automatic.toggled.connect(lambda enabled:self.preference('auto_capture',enabled));form.addRow(automatic)
        visible=QCheckBox('Mostrar overlay da Rotina');visible.setChecked(self.context.prefs.routine.panel_visible)
        visible.toggled.connect(self.toggle_panel);form.addRow(visible)
        style=QComboBox();style.addItem('Pulso compacto','pulse');style.addItem('Faixa','strip')
        style.setCurrentIndex(style.findData(self.context.prefs.routine.panel_style))
        style.currentIndexChanged.connect(lambda:self.preference('panel_style',style.currentData()));form.addRow('Estilo do overlay',style)
        locked=QCheckBox('Travar posição');locked.setChecked(self.context.prefs.routine.panel_locked)
        locked.toggled.connect(lambda enabled:self.preference('panel_locked',enabled));form.addRow(locked)
        opacity=QDoubleSpinBox();opacity.setRange(.3,1);opacity.setSingleStep(.05);opacity.setValue(self.context.prefs.routine.panel_opacity)
        opacity.valueChanged.connect(lambda value:self.preference('panel_opacity',value));form.addRow('Opacidade',opacity)
        for resource in RESOURCES:
            pin=QCheckBox(RESOURCES[resource][0]);pin.setChecked(resource in self.context.prefs.routine.pinned)
            pin.toggled.connect(lambda enabled,r=resource:self.toggle_pin(r,enabled));form.addRow(pin)
        form.addRow(label('Use o ícone de layout no overlay para trocar de estilo. A seta recolhe ou expande o painel.','subtitle',True))
        form.addRow(button('Restaurar posição',lambda:self.preference('panel_position',None)))
        form.addRow(button('Fechar',dialog.accept));dialog.exec()

    def preference(self,name,value):
        setattr(self.context.prefs.routine,name,value);self.context.save()

    def how(self):
        dialog=QDialog(self);dialog.setWindowTitle('Como funciona a Rotina');dialog.resize(500,370)
        box=QVBoxLayout(dialog);box.setSpacing(14)
        box.addWidget(label('Você joga. A Rotina acompanha.','routineName',True))
        box.addWidget(label('A leitura passiva usa a mesma conexão de Combate e Pets. Não consulta sua senha, não envia comandos e não altera o jogo.','subtitle',True))
        box.addWidget(label('O saldo inicial pode chegar antes da identificação do personagem. A Rotina espera o vínculo correto antes de salvar, para não misturar personagens.','subtitle',True))
        box.addWidget(label('Esta versão acompanha Odyle básica e recarregada separadamente. Limites, reposições, resets e outros contadores só aparecerão após validação.','subtitle',True))
        box.addWidget(label('Registros salvos mostram a hora da última leitura. Nenhuma reposição offline é estimada.','subtitle',True))
        box.addStretch();box.addWidget(button('Entendi',dialog.accept));dialog.exec()
