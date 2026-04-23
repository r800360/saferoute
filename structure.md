SafeRoute/
│
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
│
├── paper/                         # 📄 CVPR paper (self-contained)
│   ├── main.tex
│   ├── refs.bib
│   ├── cvpr.sty
│   ├── ieeenat_fullname.bst
│   ├── sections/                 # optional (cleaner edits)
│   │   ├── problem.tex
│   │   ├── approach.tex
│   │   └── results.tex
│   ├── figures/
│   └── output/
│       └── main.pdf
│
├── src/                          # 🧠 core system (pure Python)
│   ├── agents/
│   │   ├── perception.py
│   │   ├── planner.py
│   │   ├── critic.py
│   │   └── executor.py
│   │
│   ├── graph/                    # agent orchestration (LangGraph-style)
│   │   └── workflow.py
│   │
│   ├── carla_interface/          # CARLA wrapper (important abstraction)
│   │   ├── client.py
│   │   ├── sensors.py
│   │   └── controls.py
│   │
│   ├── utils/
│   │   └── logging.py
│   │
│   └── main.py                   # entry point
│
├── configs/                      # ⚙️ experiment configs
│   ├── default.yaml
│   └── weather_rain.yaml
│
├── scripts/                      # 🚀 runnable scripts
│   ├── run_demo.py
│   ├── eval.py
│   └── record_video.py
│
├── experiments/                  # 📊 outputs (gitignored mostly)
│   ├── logs/
│   ├── metrics/
│   └── rollouts/
│
├── notebooks/                    # 📓 optional analysis
│   └── visualization.ipynb
│
└── docs/                         # 📘 lightweight docs
    ├── setup.md
    └── architecture.md