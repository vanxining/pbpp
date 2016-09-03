PyBridge++
=====

A simple tool for generating Python wrapper for C++ code non-intrusively and automatically.

**NOT** ready for public use now.

## 简介

让 Python 代码可以调用现成的 C/C++ 第三方库。

这个简单的工具启发自 [PyBindGen](https://launchpad.net/pybindgen)。

重复造轮子的首要原因是 [PyBindGen](https://launchpad.net/pybindgen) 只能将生成的所有 C++ 代码都集中在一个 .cpp 文件里——这对于绑定一个大的 C++ 库是不合适的。虽然这个 .cpp 文件完全没有使用模板（与 [Boost::Python](http://www.boost.org/libs/python/doc/) 恰恰相反），但一个动辄数十万行的源文件对于常用的 C++ 编译器也并不是可以轻松对付的。

另一个原因是 [PyBindGen](https://launchpad.net/pybindgen) 不支持全局变量。[PyBindGen](https://launchpad.net/pybindgen) 本身的实现颇为复杂，要想为其加上这个功能是比较困难的。

PyBridge++ 需要配合 [CastXML](https://github.com/CastXML/CastXML) 来使用。[CastXML](https://github.com/CastXML/CastXML) 的作用是解析 C/C++ 头文件（通过调用 [Clang](http://clang.llvm.org/)），生成其接口的 XML 描述。然后 PyBridge++ 便可以根据这些 XML 接口描述自动生成相应的 Python 绑定代码。

## 用法

用户应直接与位于 Console 子目录下的可视化辅助程序进行交互：[PyBridge++ Binding Console](https://github.com/vanxining/pbpp/tree/master/Console)。

PyBridge++ Binding Console 基于 [wxWidgets](http://www.wxwidgets.org/) 来实现。此处 [wxWidgets](http://www.wxwidgets.org/) 的 Python 绑定也是由 PyBridge++ 来生成的，即为下文“示例”小节中的 [pywx](https://github.com/vanxining/pywx)。也就是说，PyBridge++ Binding Console 在某种程度上实现了自举。

具体用法请参考 Docs 子目录下的详细文档。

## 示例

一个较为完善的例子：[pywx](https://github.com/vanxining/pywx)