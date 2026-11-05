# JCVI 镜像内测试数据与边界

smoke 只在唯一临时工作目录生成确定性合成数据；没有真实受试者、病原体、生产数据库或
额外联网下载。合成序列只用于格式与比对软件工程验证，不承担科学结论。

`test_chromosome.py` 原样来自 JCVI v1.6.7 的 `tests/graphics/test_chromosome.py`，
commit `e10b8844a7539bad0a9de31f2bfe93b3c4fbd29c`。保持上游 BSD-2-Clause 许可，
源仓库随附原样 [BSD-2-Clause 通知](licenses/jcvi-BSD-2-Clause.txt)，完整许可也随镜像
保留于 `/opt/jcvi/share/licenses/jcvi/LICENSE`；Docker build 对两份原文执行 `cmp`。
五项回归只在运行期测试，不进入 QEMU Dockerfile build-time。

MCscan 用固定随机种子生成 8 对同序列、相同顺序的合成基因，经真实 LAST、anchor、
liftover、mcscan 和 headless dotplot。资源测试验证三类单文件成员、幂等、身份、校验、
inventory、合法根链接/链式链接、悬空/循环根拒绝、成员链接拒绝、损坏和本地 SO 读取；
真实持久安装与跨用户只读复用另经 wrapper/actual bind 验证。

`sam` smoke 用官方组件构造极小随机权重模型，验证 CPU tensor 路径和 torchvision NMS，
不下载或冒充完整训练模型。固定官方 ViT-H（SHA256
`a7bf3b02f3ebf1267aba913ff637d9a2d5c33d3173bb679e46d9f338c26f262e`）
通过显式资源安装器在镜像外校验；完整 CPU Grabseeds 推理、实际只读共享和文件输出在
维护者私有目录经真实 wrapper 单独验证。模型不是 SA-1B 数据集；代码和模型保持 Apache-2.0。

JCVI 1.6.9 的 `synteny` 另核对重复 HSP 的两种实际约定：blastfilter 选最高分并按 C-score 过滤，liftover 保留首条。它们属于 release smoke，不在 Dockerfile 执行。
