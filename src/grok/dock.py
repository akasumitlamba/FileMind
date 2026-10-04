from PySide6.QtCore import QRect


def geometry(area, width, expanded, position):
    width = min(width if expanded else 42, area.width())
    height = area.height() if expanded else min(86, area.height())
    y = area.y() if expanded else area.y() + round((area.height() - height) * min(1, max(0, position)))
    return QRect(area.right() - width + 1, y, width, height)
