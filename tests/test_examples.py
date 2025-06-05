from pathlib import Path

from safulate import run_code
from safulate.interpreter import Interpreter

examples_dir = Path(__file__).parent.parent / "examples"


class TestEnumExample:
    testing_code = r"""
    pub ColorRoles = Enum(
        "ColorRoles",
        blue = 0,
        red = 1,
        purple = 2,
        green = 3
    );

    ColorRoles ~ {
        assert(\name == "ColorRoles");
    };

    assert(ColorRoles.blue.name == "blue");
    assert(ColorRoles.blue.value == 0);
    assert(ColorRoles.blue:r == "ColorRoles.blue");
    assert(ColorRoles.check(ColorRoles.blue) == true);
    assert(ColorRoles.members has ColorRoles.blue);

    assert(ColorRoles.red.name == "red");
    assert(ColorRoles.red.value == 1);
    assert(ColorRoles.red:r == "ColorRoles.red");
    assert(ColorRoles.check(ColorRoles.red) == true);
    assert(ColorRoles.members has ColorRoles.red);

    assert(ColorRoles.purple.name == "purple");
    assert(ColorRoles.purple.value == 2);
    assert(ColorRoles.purple:r == "ColorRoles.purple");
    assert(ColorRoles.check(ColorRoles.purple) == true);
    assert(ColorRoles.members has ColorRoles.purple);

    assert(ColorRoles.green.name == "green");
    assert(ColorRoles.green.value == 3);
    assert(ColorRoles.green:r == "ColorRoles.green");
    assert(ColorRoles.check(ColorRoles.green) == true);
    assert(ColorRoles.members has ColorRoles.green);
    """
    file = examples_dir / "enum.saf"

    def test_enum(self) -> None:
        interpreter = Interpreter("enum.saf test")

        run_code(self.file.read_text(), interpreter=interpreter)
        run_code(self.testing_code, interpreter=interpreter)
