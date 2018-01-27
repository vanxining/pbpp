PyBridge++
===

# 概述

PyBridge++ 是一个可以为 C/C++ 代码生成 Python 绑定（binding）的工具。
PyBridge++ 受到了 PyBindGen 的启发，甚至直接用了它（很小）的一部分代码。

PyBridge++ 接受由 CastXML 生成的 C/C++ 头文件的 XML 描述，解析后输出若干 C++ 源文件。
编译这些 C++ 源文件后得到一个 Python 动态模块（.pyd）。
在 Python 代码中导入这个模块即可。

C/C++ 源文件 → CastXML (LLVM) → PyBridge++ → C++ 编译器（Visual C++/GCC/Clang/...） → .pyd 模块

CastXML 使用 LLVM/Clang 前端生成指定 C/C++ 文件的接口描述，格式为纯文本 XML。如：

```C++
#include <vector>
int foo(long threshold, const std::vector<int> &data);
```

CastXML 生成的 XML 接口描述为：

```XML
```

PyBridge++ 将这些接口映射到 Python 端。如上述函数可以在 Python 端以如下方式调用：

```Python
result = foo(100, [1, 2, 3, 4,])
```

CastXML 的更详细说明请参考其[官方页面](https://github.com/CastXML/CastXML)。

# 优势

* 非侵入式（不会修改要绑定的 C/C++ 文件）
* 少量模板（对比 Boost.Python）
* 为每一个 C++ 类生成一个单独的 C++ 文件：支持大型 C++ 项目
* 支持全局变量
* 已实例化的模板
* 支持多重继承
* 支持多线程

# 若干概念

## 工程

PyBridge++ 视每一个要生成的 .pyd 为一个工程。

## 符号

包括：
* 模块名
* 类名
* （成员）函数名
* ……

# 最佳实践

## 命名符号

## 提供额外的头文件

### 预编译头

## 管理对象的生命周期

目的是指定在 Python 分配的对象的生命周期。默认是由 Python 管理，
即当一个对象的 Python 端引用计数减为 0，就会被 Python 析构。
也可以设为由 C++ 端管理。应用场景主要是即使对象在 Python 端变为不可达
（引用计数为 0），Python 也不能销毁这个对象。对象的析构由 C++ 代码来管理。

## 符号黑名单

控制哪些符号不导出到 Python 端。

## 包裹头文件（header wrapper）

需要使用 header wrapper 的目的主要是一个头文件可能不是自包含的。
也就是说，它需要某些尚未被包含进来的符号。如

```C++
// File name: foo.h

int foo(long threshold, const std::vector<int> &data);
```

单独使用 CastXML 编译这个头文件是无法通过的，因为它缺少 std::vector<int> 的声明。
解决方法可以是使用一个 header wrapper：

```C++
// File name: foo.pbpp.h

#include <vector>
#include "foo.h"
```

关于 header wrapper 的文件名：

## 傀儡类

傀儡类的目的主要有两个：
* 暂时不想生成某个类。原因可能是这个类的外部接口中依赖太多其他未导出的 C++ 类型，
完整生成这个类的绑定可能需要大量适配工作，但我们又希望尽快使用某些使用了这个类的引用、
指针类型变量的类型或者函数
* 本身就是一个傀儡类。如 Win32 SDK 中的 `HANDLE` 以及 `HWND` 等句柄类型

## C++ 与 Python 容器之间的转换

## C++ 与 Python 字符串之间的转换

## 不导出类的某个基类

## 替换/注入某个类的成员函数

更改类接口。

## 可以感知 Python 端对象的类（Python-aware class）

## 异常

## 混杂静态成员函数与非静态成员函数的重载

以下例子暂时无法生成绑定：
```C++
class foo {
public:
    int bar(foo &);
    static int bar(foo &, foo &);
};
```
这种情况下需要删除其中一个成员函数。
需要保证所有参与重载的成员函数都是同一类型的，即同为静态或者同为非静态。
