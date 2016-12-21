import os
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET

from .. import Xml


class Blacklist(Xml.Compressor.Blacklist):

    _base_patters = [
        re.compile(r"std::_Vector_base<.+, std::allocator<.+> >"),
    ]

    _bases = [
        "UnexportedBase",
    ]

    def base(self, full_name):
        for pattern in self._base_patters:
            if pattern.match(full_name):
                return True

        return full_name in self._bases


class TestXmlCompressor(unittest.TestCase):
    def runTest(self):
        fxml_out = tempfile.gettempdir() + os.path.sep + "out.xml"

        c = Xml.Compressor()
        c.compress(headers=("compressor.hpp",),
                   fxml="Tests/raw/COMPRESSOR.xml",
                   fxml_out=fxml_out,
                   blacklist=Blacklist())

        root = ET.parse(fxml_out).getroot()

        self.assertIsNotNone(root.find("./Enumeration[@id='_5']"))
        self.assertIsNone(root.find("./Enumeration[@id='_10']"))

        self.assertIsNotNone(root.find("./Class[@name='UnexportedBase']"))
        self.assertIsNone(root.find("./Class[@name='Derived']/Base"))

        self.assertIsNotNone(root.find("./Struct[@name='Vector<int>']"))
        self.assertIsNotNone(root.find("./Struct[@name='Vector<double>']"))


'''
C++ source code generating the COMPRESSOR.xml:

```
enum class Color {
    RED,
    GREEN,
    BLUE = 255
};

class UnexportedBase {
public:
    virtual void foo();
};

class Derived {
public:
    virtual void foo();
};

template <typename T>
struct Vector {
    T data[100];
};

void TestTemplate(const Vector<int> &);

typedef Vector<double> DoubleVec;
```

Don't forget to change the file name of the <File> node.
'''
