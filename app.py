import os
import sys
import subprocess

import streamlit as st

st.set_page_config(layout='wide')


def _apply_global_sidebar_styles():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

            [data-testid="stSidebar"] {
                background: #fcf9f8 !important;
                border: 0 !important;
            }

            [data-testid="stSidebarContent"] {
                background: #fcf9f8 !important;
            }

            [data-testid="stSidebarNav"] {
                font-family: "Plus Jakarta Sans", sans-serif;
                padding-top: 0.6rem;
            }

            [data-testid="stSidebarNav"]::before {
                content: "The Intelligent Investor";
                display: block;
                font-size: 1.42rem;
                letter-spacing: -0.02em;
                line-height: 1.1;
                font-weight: 800;
                color: #004f45;
                margin: 0.4rem 0 0.25rem 0.85rem;
            }

            [data-testid="stSidebarNav"]::after {
                content: "Silent Analyst AI";
                display: block;
                font-size: 0.72rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: rgba(62, 73, 70, 0.7);
                margin: 0 0 1rem 0.9rem;
                font-weight: 700;
            }

            [data-testid="stSidebarNav"] ul {
                gap: 0.42rem;
            }

            [data-testid="stSidebarNav"] a {
                border-radius: 999px 0 0 999px;
                margin-left: 0.6rem;
                padding: 0.58rem 0.9rem;
                color: rgba(28, 27, 27, 0.66);
                font-weight: 600;
                transition: all 180ms ease;
            }

            [data-testid="stSidebarNav"] a:hover {
                background: #f2eeed;
                color: #004f45;
            }

            [data-testid="stSidebarNav"] a[aria-current="page"] {
                background: #ffffff;
                color: #004f45;
                box-shadow: 0 24px 32px rgba(28, 27, 27, 0.04);
                font-weight: 700;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


_apply_global_sidebar_styles()


protected_pages = [
    st.Page('pages/chat.py', title='Chat'),
    st.Page('pages/generate.py', title='Gerar Relatório'),
    st.Page('pages/portfolio.py', title='Portfolio'),
    st.Page('pages/reports.py', title='Meus Relatórios'),
    st.Page('pages/settings.py', title='Configurações'),
]

pg = st.navigation(protected_pages)
pg.run()


if __name__ == '__main__':
    # Obtém o caminho absoluto do diretório atual
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Caminho para o arquivo app.py
    app_path = os.path.join(current_dir, 'app.py')

    # Executa o comando streamlit run app.py
    subprocess.run([sys.executable, '-m', 'streamlit', 'run', app_path])
