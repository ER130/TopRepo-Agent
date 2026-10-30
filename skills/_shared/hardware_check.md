# Shared hardware check

Reference, not a skill (not named `SKILL.md`, so it's never loaded or
listed automatically). `msconvert`, `toppic_suite`, `toprepo_pipeline`
and `pdpred_pipeline` each point here before their first long-running
command. It exists because tool defaults are not tuned to the machine:
TopFD and TopPIC default to **one thread**, and on this project a TopPIC
run used 1 of 16 cores because nobody checked.

## 1. Check the machine -- before writing the plan

Run these once per session (the answers don't change mid-run) and put
the results in the plan:

```
nproc                                   # CPU cores
free -g                                 # memory: total and available, in GB
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv \
    2>/dev/null || echo "no NVIDIA GPU"
df -h <data dir>                        # free disk where outputs will go
grep -qi microsoft /proc/version && echo WSL
```

**Where the data is -- always its own line in the plan.** Under WSL, a
path on `/mnt/<drive>/` is the Windows disk, reached through a slow
translation layer -- TopFD/TopPIC run much slower there. Noting
"data on /mnt/d" in the machine summary isn't enough (agents have done
that twice and moved on). For a long run, suggest working in a
folder on the Linux filesystem instead (e.g. `~/toprepo_runs/<run_name>/`
-- note the project folder itself may be on `/mnt/<drive>/` too, check
with `pwd`) and copying the results back afterwards; say why, and let the
user decide. (`msconvert` is the exception: it's a Windows
program and needs its files on `/mnt/<drive>/`.)

## 2. Choose resource parameters from the check

| Tool | Parameter | Default if unset | Rule |
|---|---|---|---|
| TopFD, TopPIC | `-u` threads | 1 | `cores - 1` (leave one for the system). Reduce if available memory is low -- see below |
| `toprepo_pipeline`'s `mgf_anno_file.py` | `--num_workers` | `cores - 1` | Keep the default unless something else is running |
| PDpred training (`train_td_pred.py`) | device, `--batch` | GPU if PyTorch sees one, else CPU; batch 32 | Say in the plan which it will use. On CPU, training is far slower: estimate time from one epoch before committing to many. Multi-GPU: `torchrun --nproc_per_node=<GPUs>` |
| PDpred prediction (`td_pred.py`) | -- | GPU if available | No resource flags; just report which device it used |
| msconvert | -- | -- | No thread flag. Convert files one at a time |

**Memory (not measured on this project -- a conservative rule of
thumb).** TopFD/TopPIC's documentation asks for at least 16 GB and gives
no per-thread figure. If available memory is under 16 GB, say so before
running, and start with `-u 4` rather than `cores - 1`; if a run is
killed with no error message (the usual sign of running out of memory),
halve `-u` and tell the user. When a real run's peak memory is known
(`/usr/bin/time -v <command>` reports "Maximum resident set size"),
replace this paragraph with the measured number.

**One job at a time by default** (`code.py` also queues heavy
background jobs -- TopFD, TopPIC, msconvert, TD-Pred -- so a second one
waits for the first; plan the order yourself regardless). Run several files of the same step one
after another, each with the full thread count. Two jobs at once, each
with `-u <cores - 1>`, oversubscribe the CPU and run no faster -- and
two TopPIC runs against the same FASTA also compete for its
`<database>.fasta_idx/` index. If the user asks to run several at once,
split the cores between them (e.g. two jobs on 16 cores: `-u 7` each).

## 3. Put it in the plan, then in run_log.txt

In the plan, one line per long-running step, with the evidence:

```
Machine: 16 cores, 31 GB free, no GPU
Data:   on /mnt/d (WSL, slow) -> suggest working in ~/toprepo_runs/st_test/,
        copying results back to runs/st_test/ -- your call
TopFD:  -u 15, st_1 then st_2 (one at a time)
TopPIC: -u 15, st_1 then st_2
```

After the step finishes, include the values actually used in its
`run_log.txt` line (see `run_layout.md`), e.g.
`toppic_suite  st_1/st_2: TopFD -u 15, TopPIC -u 15 -f C57, sequential`.
