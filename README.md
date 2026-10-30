# ASC27 校内选拔赛提交材料

林佳逸 · 202440025315 · 24级软件工程

本目录包含两道赛题的代码、配置和实验材料。复现过程、优化方法、运行环境及结果对比见报告：

- [赛题一：HPL 与 HPCG 性能优化](赛题一_HPL与HPCG性能优化报告_林佳逸.pdf)
- [赛题二：具身世界模型推理优化](赛题二_具身智能模型优化报告_林佳逸.pdf)

## 文件位置

| 路径 | 内容 |
| --- | --- |
| `asc27/src/` | HPL、HPCG 源码、优化版本及编译输出 |
| `asc27/scnu_asc/` | HPL、HPCG 配置文件与编译配置 |
| `code/unifolm-world-model-action/` | 世界模型项目源码及优化后的推理代码 |
| `code/competition_data/`、`code/eval_data/` | 官方输入、参考视频和推理所需数据 |
| `code/environment/`、`code/patches/` | 环境版本记录与代码修改差异 |
| `proposal_file/` | PSNR 图表、运行界面截图、视频帧截图 |
| `results/` | 赛题二两个场景各 4 个 case 的结果及 `summary.json` |

每个 `results/<scenario>/caseN/` 目录包含最终 MP4、`output.log` 和 `psnr.json`。两份报告 PDF 放在本目录根目录。

## 项目分享
- Colab 分享链接：具体原因请移步到赛题二的报告，赛题二在AutoDL租用的服务器上完成，所以并无Colab分享链接
