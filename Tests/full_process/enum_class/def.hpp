enum class Color {
    RED,
    GREEN,
    BLUE = 255
};

typedef Color &ColorRef;

Color *get_color();

ColorRef get_color_ref();

Color use_color(Color *color);

Color use_color_ref(ColorRef color);

Color use_color_const_ref(const Color &color = Color::BLUE);
