#include "def.hpp"

static Color gs_color = Color::GREEN;

Color *get_color() {
    return &gs_color;
}

ColorRef get_color_ref() {
    return gs_color;
}

Color use_color(Color *color) {
    *color = Color::BLUE;
    return *color;
}

Color use_color_ref(ColorRef color) {
    color = Color::RED;
    return color;
}

Color use_color_const_ref(const Color &color) {
    return color;
}
