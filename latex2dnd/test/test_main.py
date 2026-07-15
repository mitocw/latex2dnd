from latex2dnd.main import Box


def test_png_geom_bottom_trim_only_changes_height():
    box = Box.__new__(Box)
    box.png_pos = lambda imx, imy: [10, 110, 210, 20]

    assert box.png_geom(300, 200, delta=4.5) == "191x81+14+28"
    assert box.png_geom(
        300, 200, delta=4.5, bottom_trim=4
    ) == "191x77+14+28"
