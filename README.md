PyBridge++
=====

A simple tool for generating Python wrapper for C++ code automatically.

Under development, this code has not been ready for public use now.

## 中文

这个软件其实是在 [PyBindGen](https://launchpad.net/pybindgen) 的启发下开发出来的。为什么有了这样一个优雅的解决方案，我还要重复造轮子呢？

首要原因是 [PyBindGen](https://launchpad.net/pybindgen) 只能将生成的所有 C++ 代码都集中在一个 .cpp 文件里——这对于绑定一个大的 C++ 库是不合适的。虽然 [PyBindGen](https://launchpad.net/pybindgen) 完全没有使用模板，但当前各家 C++ 编译器对于一个动辄 10k+ 行的 .cpp 文件想来还是有点力不从心的。

另一个原因是 [PyBindGen](https://launchpad.net/pybindgen) 不支持全局变量，而且作者短期内也没有为它添加这个特性的计划。[PyBindGen](https://launchpad.net/pybindgen) 本身的实现颇为复杂，普通用户要想对其做一些修改是很困难的，因此我就萌生了写一个功能较少的“山寨版”的想法，也就有了这个项目。

需要配合 [CastXML](https://github.com/CastXML/CastXML) 使用。[CastXML](https://github.com/CastXML/CastXML) 在此起的作用是解析 C++ 头文件，生成其接口的 XML 描述。然后 PyBridge++ 便可以根据这些 XML 接口声明自动生成相应的 Python 端绑定代码。

## 示例

一个较为完善的例子：[pywx](https://github.com/vanxining/pywx)