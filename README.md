pybpp
=====

A simple tool for generating Python wrapper for C++ code automatically.

Under development, this code has not been ready for public use now.

## 中文来了

这个软件其实是在 [PyBindGen](http://code.google.com/p/pybindgen/ "PyBindGen") 的启发下开发出来的。为什么有了这样一个优雅的解决方案你还要重复造轮子呢？

首要原因是 [PyBindGen](http://code.google.com/p/pybindgen/ "PyBindGen") 只能将生成的所有 `C++` 代码都集中在一个 `.cpp` 文件里——这对于绑定一个极大的 `C++` 库是非常不合适的。虽然 [PyBindGen](http://code.google.com/p/pybindgen/ "PyBindGen") 没有完全使用模板，但当前各家 `C++` 编译器对于一个动辄 10k+ 行的 `.cpp` 文件还是有点力不从心的。

另一个原因是 [PyBindGen](http://code.google.com/p/pybindgen/ "PyBindGen") 不支持全局变量，而且作者短期内也没有为它添加这个特性的计划。我本欲动手加上去，奈何看别人写的代码实在是天底下第一难事，我一般极力避免，故而只好自己再造一个轮子了。