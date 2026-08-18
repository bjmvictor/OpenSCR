from datetime import datetime
import getpass
import platform
import socket


WEEKDAYS = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
]

MONTHS = [
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]


AVAILABLE_VARIABLES = {
    "{date}": "Data atual - 18/08/2026",
    "{time}": "Hora atual - 14:35",
    "{time_seconds}": "Hora com segundos - 14:35:27",
    "{date_time}": "Data e hora - 18/08/2026 14:35",
    "{day}": "Dia do mês - 18",
    "{weekday}": "Dia da semana - Terça-feira",
    "{month}": "Número do mês - 08",
    "{month_name}": "Nome do mês - Agosto",
    "{year}": "Ano - 2026",
    "{computer}": "Nome do computador",
    "{user}": "Usuário do Windows",
    "{os}": "Sistema operacional",
}


def get_variables():
    now = datetime.now()

    return {
        "{date}": now.strftime("%d/%m/%Y"),
        "{time}": now.strftime("%H:%M"),
        "{time_seconds}": now.strftime("%H:%M:%S"),
        "{date_time}": now.strftime("%d/%m/%Y %H:%M"),
        "{day}": now.strftime("%d"),
        "{weekday}": WEEKDAYS[now.weekday()],
        "{month}": now.strftime("%m"),
        "{month_name}": MONTHS[now.month - 1],
        "{year}": now.strftime("%Y"),
        "{computer}": socket.gethostname(),
        "{user}": getpass.getuser(),
        "{os}": platform.system(),
    }


def render_variables(text: str) -> str:
    variables = get_variables()

    for variable, value in variables.items():
        text = text.replace(variable, value)

    return text