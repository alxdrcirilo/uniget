# Source: https://stackoverflow.com/a/46096319 (11/02/2022)

from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem


class ViewTree(QTreeWidget):
    def __init__(self, value):
        super().__init__()

        def fill_item(item, value):
            def new_item(parent, text, val=None):
                child = QTreeWidgetItem([text])
                fill_item(child, val)
                parent.addChild(child)
                child.setExpanded(False)

            if value is None:
                return
            elif isinstance(value, dict):
                for key, val in sorted(value.items()):
                    new_item(item, str(key), val)
            elif isinstance(value, (list, tuple)):
                for val in value:
                    text = (
                        str(val)
                        if not isinstance(val, (dict, list, tuple))
                        else f"[{type(val).__name__}]"
                    )
                    new_item(item, text, val)
            else:
                new_item(item, str(value))

        fill_item(self.invisibleRootItem(), value)
