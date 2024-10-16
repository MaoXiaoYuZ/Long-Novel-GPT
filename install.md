# 一些已知的安装问题

## ModuleNotFoundError: No module named 'pyaudioop'

即使gradio安装成功，import gradio也可能出现这个错误，原因未知。不过可以通过安装这个库解决：

```bash
pip install audioop-lts
```

