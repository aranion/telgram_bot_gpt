import datetime


def add_secs_to_datetime(date, secs_to_add):
    """Добавляет указанное количество секунд к заданному времени.

    Args:
        date(datetime.datetime): Исходное время.
        secs_to_add (int): Количество секунд, которые нужно добавить.

    Returns:
        datetime.datetime: Новое время с добавленными секундами.
    """

    new_time = date + datetime.timedelta(seconds=secs_to_add)

    return new_time
