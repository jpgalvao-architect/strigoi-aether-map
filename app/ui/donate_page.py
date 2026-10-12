# SPDX-License-Identifier: GPL-3.0-only
"""External official donation channels; the app never processes a payment."""
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QVBoxLayout
from app.ui.localized_widgets import QWidget
from app.ui.widgets import button, card, label, page_header

CREATOR_URL='https://link.mercadopago.com.br/thothworlds'
CREATOR_MESSAGE='Curtiu o Strigoi? Se meu trabalho te ajudou e você quiser retribuir, pode deixar uma força por aqui. Sem pressão: usar o app, mandar feedback e compartilhar com a galera já ajuda demais.'

INSTITUTIONS=(
    {'name':'Associação dos Surdos de São José dos Pinhais · ASSJP',
     'description':'Associação civil que promove atividades sociais, culturais e esportivas para a comunidade surda.',
     'url':'https://assjp.org.br/junte-nos/seja-apoiador/',
     'guide':'O canal oficial apresenta as formas de doação e apoio.'},
    {'name':'Associação dos Surdos de Contagem · ASC',
     'description':'Associação sem fins lucrativos dedicada aos direitos, à acessibilidade e à inclusão de pessoas surdas.',
     'url':'https://www.ascontagem.org.br/',
     'guide':'No site oficial, abra Doações para consultar as formas de contribuir.'},
)


class DonatePage(QWidget):
    def __init__(self):
        super().__init__()
        layout=QVBoxLayout(self);layout.setContentsMargins(26,20,26,20)
        layout.addWidget(page_header('Donate','Apoie quem criou o app ou uma instituição da comunidade surda.'))
        creator,body=card()
        body.addWidget(label('Uma força pra quem fez o Strigoi',wrap=True))
        body.addWidget(label(CREATOR_MESSAGE,'subtitle',True))
        self.creator_button=button('Apoiar o criador · Mercado Pago',lambda:self.open_channel(CREATOR_URL),True)
        self.creator_button.setAccessibleName('Apoiar o criador pelo Mercado Pago')
        self.creator_button.setToolTip(CREATOR_URL)
        body.addWidget(self.creator_button)
        body.addWidget(label('Este apoio é destinado ao criador do app.','subtitle',True))
        layout.addWidget(creator)
        layout.addWidget(label('Apoiar a comunidade surda','eyebrow'))
        layout.addWidget(label('Escolha uma instituição brasileira que apoia pessoas surdas. Sua contribuição é feita diretamente pelo canal oficial da instituição.','subtitle',True))
        self.buttons=[]
        for institution in INSTITUTIONS:
            frame,body=card()
            body.addWidget(label(institution['name'],wrap=True))
            body.addWidget(label(institution['description'],'subtitle',True))
            body.addWidget(label(institution['guide'],'subtitle',True))
            action=button('Abrir canal oficial de apoio',lambda checked=False,url=institution['url']:self.open_channel(url),True)
            action.setAccessibleName('Abrir canal oficial de '+institution['name'])
            action.setToolTip(institution['url'])
            body.addWidget(action);layout.addWidget(frame);self.buttons.append(action)
        layout.addWidget(label('O apoio ao criador é feito pelo Mercado Pago. As doações às instituições vão diretamente para os canais de cada uma.','subtitle',True))
        layout.addStretch()

    def open_channel(self,url):
        if url not in {CREATOR_URL,*[item['url'] for item in INSTITUTIONS]}:
            return
        QDesktopServices.openUrl(QUrl(url))
