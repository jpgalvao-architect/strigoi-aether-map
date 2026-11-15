# SPDX-License-Identifier: GPL-3.0-only
"""On-screen selection and physical/logical coordinate conversion."""
from pydantic import Field, model_validator
from typing import Literal

from app.core.models import Model


class CaptureArea(Model):
    schema_version: int = 1
    map_id: str
    screen_name: str
    screen_x: int
    screen_y: int
    screen_width: int = Field(ge=100)
    screen_height: int = Field(ge=100)
    pixel_ratio: float = Field(gt=0, le=8)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(ge=80)
    height: int = Field(ge=80)
    view_kind: Literal["large", "minimap"] = "large"

    @model_validator(mode="after")
    def contained(self):
        if self.x+self.width > self.screen_width or self.y+self.height > self.screen_height:
            raise ValueError("A seleção precisa ficar dentro do monitor")
        return self

    def on_screen(self, screen):
        """Rebase the saved selection to the current logical screen geometry."""
        geometry = screen.geometry()
        sx = geometry.width() / self.screen_width
        sy = geometry.height() / self.screen_height
        x, y = round(self.x * sx), round(self.y * sy)
        return CaptureArea(
            map_id=self.map_id, screen_name=screen.name(),
            screen_x=geometry.x(), screen_y=geometry.y(),
            screen_width=geometry.width(), screen_height=geometry.height(),
            pixel_ratio=screen.devicePixelRatio(), view_kind=self.view_kind,
            x=x, y=y, width=round((self.x+self.width)*sx)-x,
            height=round((self.y+self.height)*sy)-y,
        )


def physical_region(area, monitor):
    """MSS provides physical monitor origins, including mixed-DPI and negative origins."""
    r = area.pixel_ratio
    if abs(monitor['width']-area.screen_width*r)>3 or abs(monitor['height']-area.screen_height*r)>3:
        raise ValueError("Resolução ou escala do monitor mudou. Selecione a área novamente.")
    x0, y0 = round(area.x*r), round(area.y*r)
    x1, y1 = round((area.x+area.width)*r), round((area.y+area.height)*r)
    return dict(left=monitor['left']+x0, top=monitor['top']+y0, width=x1-x0, height=y1-y0)


def find_monitor(area, monitors):
    candidates = [m for m in monitors if m['left']==area.screen_x and m['top']==area.screen_y
                  and abs(m['width']-area.screen_width*area.pixel_ratio)<3
                  and abs(m['height']-area.screen_height*area.pixel_ratio)<3]
    if len(candidates)!=1:
        raise ValueError("O monitor selecionado mudou. Escolha a área novamente.")
    return candidates[0]
