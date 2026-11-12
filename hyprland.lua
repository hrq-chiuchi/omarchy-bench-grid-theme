-- Bench Grid windows: amber border on the focused tile, mat-line border on the rest, and the
-- same 8px corners as the floating bar card, and the mockup's 8px spacing. (Replaces Omarchy's generated hyprland.lua.)
local active_border_color = "rgb(f3a712)"
local inactive_border_color = "rgb(42584d)"

hl.config({
  general = {
    -- The mockup's 8px rhythm: 8 from the screen edge (matches [bar] inset in shell.bar.toml, so the
    -- bar card lines up with the window borders) and 8 between windows (2 x gaps_in).
    gaps_out = 8,
    gaps_in = 4,
    col = {
      active_border = active_border_color,
      inactive_border = inactive_border_color,
    },
  },

  group = {
    col = {
      border_active = active_border_color,
      border_inactive = inactive_border_color,
    },
  },

  decoration = {
    rounding = 8,
    rounding_power = 2,
  },
})
