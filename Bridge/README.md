# 桥梁表观病害智能检测平台

## 目录结构

```
BridgeVision/
├── app.py                  # 主 Web 服务与路由/API
├── report_export.py        # 报告导出逻辑
├── requirements.txt        # Python 依赖
├── app.db                  # 应用数据库（运行时生成）
├── platform.db             # 平台数据库（运行时生成）
│
├── templates/              # 页面模板
│   ├── layout.html         # 公共布局
│   ├── index.html          # 首页
│   ├── detect.html         # 检测页
│   ├── realtime.html       # 实时检测
│   ├── dashboard.html      # 仪表盘
│   ├── analysis.html       # 分析页
│   ├── results.html        # 结果页
│   ├── reports.html        # 报告页
│   ├── archives.html       # 档案页
│   ├── model.html          # 模型管理
│   ├── profile.html        # 个人中心
│   ├── login.html          # 登录
│   ├── register.html       # 注册
│   ├── data.html           # 数据管理
│   └── tasks.html          # 任务管理
│
├── static/                 # 静态资源
│   ├── css/                # 样式文件
│   ├── js/                 # 前端脚本
│   └── img/                # 图片资源
│
├── modules/                # 自定义网络模块（推理侧）
│   ├── attention.py
│   ├── bifpn.py
│   ├── grb.py
│   ├── losses.py
│   ├── msdc.py
│   └── segment_p2.py
│
├── models/                 # 训练好的模型权重
│   ├── model1.0/
│   ├── model2.0/
│   ├── model3.0/
│   ├── model4.0/
│   ├── model5.0/
│   ├── model6.0/
│   ├── model7.0/
│   └── model8.0/
│
├── train_model/            # 训练相关脚本与配置
│   ├── train_exp.py        # 训练入口
│   ├── run_ablation.py     # 消融实验
│   ├── register_modules.py # 自定义模块注册
│   ├── configs/            # 实验配置文件
│   └── modules/            # 自定义网络模块（训练侧）
│
├── uploads/                # 上传文件目录（运行时生成）
└── results/                # 推理输出目录（运行时生成）
```
