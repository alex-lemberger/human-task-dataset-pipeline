# Human-Task Dataset Pipeline (v0.1)

Consent-based human-task dataset pipeline for robotics. Filesystem-only spine with CLI.

## Usage

```bash
uv sync --extra ingest    # install optional pyxdf dependency
htdp ingest input.xdf ingest.json --out data/raw     # ingest LSL recording
htdp synth --out data/raw                              # generate synthetic session
htdp validate data/raw/<session_id>                     # validate raw folder
htdp process data/raw/<session_id>                      # process to Parquet
htdp qc data/processed/<session_id>                     # QC report
htdp package --release <name> --profile <profile> <id..>  # consent-gated release
htdp replay data/releases/<name>                        # MuJoCo mocap replay
```

See [docs/ROADMAP.md](docs/ROADMAP.md) and [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md).
