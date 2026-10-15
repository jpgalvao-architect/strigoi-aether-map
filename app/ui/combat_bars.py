# SPDX-License-Identifier: GPL-3.0-only
"""Impacto: proportional DPS rows painted only when their data changes."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QFont
from PySide6.QtWidgets import QAbstractButton
from app.core.i18n import tr, language
from app.ui.combat_classes import class_color, class_label, colored_class_icon


def ranked_rows(snapshot):
    # Never mutate the engine/history snapshot or invent DPS for missing identities.
    rows = sorted((dict(r) for r in snapshot['rows']),
                  key=lambda r: (-(r.get('dps') or 0), -(r.get('damage') or 0), r.get('rank') or 0))
    highest = max((r.get('dps') or 0 for r in rows), default=0)
    previous = None
    for index, row in enumerate(rows, 1):
        score = row.get('dps') or 0
        if score != previous: rank = index
        previous = score
        row['rank'] = rank
        row['fraction'] = min(1, max(0, score/highest)) if highest else 0
    if snapshot['unattributed']:
        rows.append(dict(name=tr('Não atribuído'), damage=snapshot['unattributed'], dps=None,
                         share=snapshot['unattributed']/snapshot['total'] if snapshot['total'] else 0,
                         rank=None, job=0, local=False, fraction=0))
    return rows


class DpsRow(QAbstractButton):
    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = {}
        self.locale = None
        self.expanded = False
        self.details = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.clicked.connect(self.toggle_details)
        self.set_data(item)

    def set_data(self, item):
        if item != self.item or self.locale != language():
            self.locale = language()
            self.item = item
            from app.ui.combat_page import short_number
            name = item.get('name') or tr('Participante não identificado')
            self.setAccessibleName(f"{name} · {short_number(item.get('dps'))} DPS")
            self.setToolTip(f"{name} · {class_label(item.get('job',0))}\n{item['damage']:,} · {item['share']*100:.1f}%")
            self.update()
        self.setFixedHeight(55 if self.expanded or self.details else 39)

    def toggle_details(self):
        self.expanded = not self.expanded
        self.set_data(self.item)
        self.update()

    def set_details(self, enabled):
        changed = self.details != enabled
        self.details = enabled
        self.set_data(self.item)
        if changed:self.update()

    def retranslate(self):
        self.set_data(self.item)

    def paintEvent(self, event):
        from app.ui.combat_page import short_number
        item = self.item
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rectangle = QRectF(self.rect())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#20202c'))
        painter.drawRoundedRect(rectangle,5,5)
        painter.save()
        from PySide6.QtGui import QPainterPath
        path = QPainterPath(); path.addRoundedRect(rectangle,5,5); painter.setClipPath(path)
        color = QColor(class_color(item.get('job',0)))
        width = rectangle.width()*item.get('fraction',0)
        if width:
            gradient = QLinearGradient(0,0,max(1,width),0)
            shade = QColor(color); shade.setAlpha(86); gradient.setColorAt(0,shade)
            shade.setAlpha(38); gradient.setColorAt(1,shade)
            painter.fillRect(QRectF(0,0,width,self.height()),gradient)
            painter.fillRect(QRectF(max(0,width-2),0,2,self.height()),color)
        painter.restore()
        font = QFont('Segoe UI'); font.setPixelSize(10); painter.setFont(font)
        painter.setPen(QColor('#aaa8bd'))
        painter.drawText(QRectF(5,0,16,39),Qt.AlignmentFlag.AlignCenter,str(item['rank'] or '—'))
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor('#10131c'))
        painter.drawRoundedRect(QRectF(25,6,27,27),5,5)
        colored_class_icon(item.get('job',0)).paint(painter,28,8,21,23)
        font.setPixelSize(12); font.setWeight(QFont.Weight.DemiBold); painter.setFont(font)
        painter.setPen(QColor('#eeedf8'))
        value = short_number(item.get('dps'))+' DPS'
        font.setPixelSize(14);painter.setFont(font)
        value_width = max(65,painter.fontMetrics().horizontalAdvance(value)+6)
        name_width = max(0,self.width()-68-value_width)
        font.setPixelSize(12);painter.setFont(font)
        name = item.get('name') or tr('Participante não identificado')
        if item.get('local'): name += tr(' · você')
        name = painter.fontMetrics().elidedText(name,Qt.TextElideMode.ElideRight,name_width)
        painter.drawText(QRectF(60,0,name_width,39),Qt.AlignmentFlag.AlignVCenter,name)
        font.setPixelSize(14); painter.setFont(font)
        painter.drawText(QRectF(self.width()-value_width-8,0,value_width,39),
                         Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,value)
        if self.expanded or self.details:
            font.setPixelSize(10); font.setWeight(QFont.Weight.Normal); painter.setFont(font)
            painter.setPen(QColor('#aaa8bd'))
            painter.drawText(QRectF(60,34,self.width()-70,17),Qt.AlignmentFlag.AlignVCenter,
                             tr('{dano} de dano · {parte}%').format(dano=short_number(item['damage']),parte=f"{item['share']*100:.1f}"))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QColor('#c2b2fc'))
            painter.drawRoundedRect(rectangle.adjusted(.5,.5,-.5,-.5),5,5)
