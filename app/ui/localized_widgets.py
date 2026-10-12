# SPDX-License-Identifier: GPL-3.0-only
"""Qt controls remember source captions so language switches do not lose state."""
from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from app.core.i18n import tr

TEXT_ROLE = int(Qt.ItemDataRole.UserRole)+481
TIP_ROLE = TEXT_ROLE+1


class _TextMixin:
    def __init__(self, *args, **kwargs):
        self._captions = {}
        super().__init__(*args, **kwargs)
        for getter, setter in [('text','setText'),('title','setTitle'),('windowTitle','setWindowTitle')]:
            method = getattr(super(),getter,None)
            if getter=='text' and isinstance(self,QtWidgets.QLineEdit):
                continue
            if method and method():
                getattr(self,setter)(method())

    def _caption(self, setter, text):
        self._captions[setter] = text
        getattr(super(),setter)(tr(text))

    def setText(self,text):
        if isinstance(self,QtWidgets.QLineEdit):
            super().setText(text)
        else:self._caption('setText',text)
    def setTitle(self,text): self._caption('setTitle',text)
    def setWindowTitle(self,text): self._caption('setWindowTitle',text)
    def setToolTip(self,text): self._caption('setToolTip',text)
    def setAccessibleName(self,text): self._caption('setAccessibleName',text)
    def setPlaceholderText(self,text): self._caption('setPlaceholderText',text)
    def setSuffix(self,text): self._caption('setSuffix',text)
    def setPrefix(self,text): self._caption('setPrefix',text)

    def retranslate(self):
        for setter,source in self._captions.items():
            getattr(super(),setter)(tr(source))


for _name in ['QLabel','QPushButton','QToolButton','QCheckBox','QGroupBox','QFrame',
              'QWidget','QLineEdit','QSpinBox','QDoubleSpinBox','QDialog']:
    globals()[_name] = type(_name,(_TextMixin,getattr(QtWidgets,_name)),{})


class QStatusBar(QtWidgets.QStatusBar):
    def showMessage(self,text,timeout=0):
        self._message=(text,timeout)
        super().showMessage(tr(text),timeout)

    def clearMessage(self):
        self._message=('',0)
        super().clearMessage()

    def retranslate(self):
        if self.currentMessage() and hasattr(self,'_message'):
            super().showMessage(tr(self._message[0]),self._message[1])


class QMainWindow(_TextMixin,QtWidgets.QMainWindow):
    def statusBar(self):
        if not hasattr(self,'_localized_status'):
            self._localized_status=QStatusBar(self)
            self.setStatusBar(self._localized_status)
        return self._localized_status


class QComboBox(_TextMixin, QtWidgets.QComboBox):
    def addItem(self,*args):
        args=list(args)
        position=0 if isinstance(args[0],str) else 1
        source=args[position]
        args[position]=tr(source)
        super().addItem(*args)
        super().setItemData(self.count()-1,source,TEXT_ROLE)

    def addItems(self,texts):
        for text in texts:self.addItem(text)

    def setItemData(self,index,value,role=Qt.ItemDataRole.UserRole):
        if role==Qt.ItemDataRole.ToolTipRole:
            super().setItemData(index,value,TIP_ROLE)
            value=tr(value)
        super().setItemData(index,value,role)

    def setCurrentText(self,text):
        super().setCurrentText(tr(text))

    def retranslate(self):
        super().retranslate()
        blocked=self.blockSignals(True)
        try:
            for index in range(self.count()):
                source=self.itemData(index,TEXT_ROLE)
                if source is not None:super().setItemText(index,tr(source))
                tooltip=self.itemData(index,TIP_ROLE)
                if tooltip is not None:super().setItemData(index,tr(tooltip),Qt.ItemDataRole.ToolTipRole)
        finally:self.blockSignals(blocked)


class QFormLayout(QtWidgets.QFormLayout):
    def addRow(self,*args):
        args=list(args)
        if args and isinstance(args[0],str):args[0]=QLabel(args[0])
        return super().addRow(*args)


class QTableWidgetItem(QtWidgets.QTableWidgetItem):
    def __init__(self,*args):
        args=list(args)
        position=next((i for i,value in enumerate(args) if isinstance(value,str)),None)
        source=args[position] if position is not None else ''
        if position is not None:args[position]=tr(source)
        super().__init__(*args)
        self.setData(TEXT_ROLE,source)

    def setText(self,text):
        self.setData(TEXT_ROLE,text)
        super().setText(tr(text))

    def setToolTip(self,text):
        self.setData(TIP_ROLE,text)
        super().setToolTip(tr(text))

    def retranslate(self):
        super().setText(tr(self.data(TEXT_ROLE) or ''))
        if self.data(TIP_ROLE) is not None:super().setToolTip(tr(self.data(TIP_ROLE)))


class QTableWidget(QtWidgets.QTableWidget):
    def setHorizontalHeaderLabels(self,values):
        self._headers=list(values)
        super().setHorizontalHeaderLabels([tr(value) for value in values])

    def retranslate(self):
        if hasattr(self,'_headers'):super().setHorizontalHeaderLabels([tr(v) for v in self._headers])
        for row in range(self.rowCount()):
            for column in range(self.columnCount()):
                item=self.item(row,column)
                if isinstance(item,QTableWidgetItem):item.retranslate()


class QMenu(_TextMixin,QtWidgets.QMenu):
    def addAction(self,*args):
        values=list(args)
        position=next((i for i,v in enumerate(values) if isinstance(v,str)),None)
        source=values[position] if position is not None else None
        if position is not None:values[position]=tr(source)
        action=super().addAction(*values)
        if source is not None:action.setProperty('sourceCaption',source)
        return action

    def retranslate(self):
        super().retranslate()
        for action in self.actions():
            source=action.property('sourceCaption')
            if source is not None:action.setText(tr(source))


class QMessageBox(QtWidgets.QMessageBox):
    @staticmethod
    def information(parent,title,text,*args):return QtWidgets.QMessageBox.information(parent,tr(title),tr(text),*args)
    @staticmethod
    def warning(parent,title,text,*args):return QtWidgets.QMessageBox.warning(parent,tr(title),tr(text),*args)
    @staticmethod
    def critical(parent,title,text,*args):return QtWidgets.QMessageBox.critical(parent,tr(title),tr(text),*args)
    @staticmethod
    def question(parent,title,text,*args):return QtWidgets.QMessageBox.question(parent,tr(title),tr(text),*args)


class QFileDialog(QtWidgets.QFileDialog):
    @staticmethod
    def getOpenFileName(parent,title,*args):return QtWidgets.QFileDialog.getOpenFileName(parent,tr(title),*args)
    @staticmethod
    def getSaveFileName(parent,title,*args):return QtWidgets.QFileDialog.getSaveFileName(parent,tr(title),*args)


def retranslate_widgets(app):
    for widget in app.allWidgets():
        method=getattr(widget,'retranslate',None)
        if method:method()
