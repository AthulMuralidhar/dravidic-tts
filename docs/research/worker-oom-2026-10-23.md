# PDF speech worker termination investigation — 2026-10-23

## Confirmed finding

The worker termination at 05:10:04 IST was a Linux global out-of-memory kill
inside Docker Desktop's WSL VM. This is established by the kernel log, which
names the exact active worker container and Python process. The earlier
`docker inspect` result `OOMKilled=false` did not capture this global OOM
event and was insufficient to rule out memory exhaustion.

This finding concerns the 05:10 termination. The earlier Windows freeze and
user-initiated power-button restart at 02:35 remain a separate incident; this
investigation does not establish the cause of that freeze.

## Primary local evidence

Docker VM log:

`C:\Users\athul\AppData\Local\Docker\log\vm\init.log.3`

At `2026-10-22T23:40:03Z` (05:10:03 IST), this log records
`python invoked oom-killer` and the OOM-tracer event. The kernel ring buffer,
read with `wsl.exe -d docker-desktop -u root -- dmesg`, retains the details:

```text
Free swap  = 0kB
Total swap = 4194304kB
oom-kill:constraint=CONSTRAINT_NONE,...,global_oom,
task_memcg=/docker/207af5b1c4721b1e930c9262b5dae94e3edff390e2c809b2b6fe8e62b712d381,
task=python,pid=2027,uid=10001
Out of memory: Killed process 2027 (python) total-vm:24628916kB,
anon-rss:13189520kB, file-rss:0kB, shmem-rss:0kB
```

The kernel's task table also shows `rss=3297380` and `swapents=996196`
4-KiB pages for that Python process. The process therefore held roughly
12.58 GiB of resident anonymous memory and 3.80 GiB of swapped memory.
All 4 GiB of VM swap was exhausted.

Matching Docker state/event evidence before recovery:

- container: `207af5b1c4721b1e930c9262b5dae94e3edff390e2c809b2b6fe8e62b712d381`;
- exit code: 137, consistent with SIGKILL;
- exit time: `2026-10-22T23:40:04.255533683Z`;
- `OOMKilled=false`, despite the kernel evidence above;
- last completed work: part 7, neural chunk 7 of 12;
- no Windows reboot or sleep event was found around this stop;
- Windows boot time remained 02:35:22 IST;
- the audio server retained its existing start time and continued serving.

Docker host log `log/host/monitor.log.5` also records the backend OOM-kill
analytics event at approximately 05:10:03 IST. No credential or authentication
files were accessed for this investigation.

## Configuration and source review

The Docker VM exposes approximately 13.56 GiB RAM and 4 GiB swap. The worker
has no explicit container memory limit (`Memory=0`, `MemorySwap=0`) and no CPU
quota. It can therefore compete for essentially the VM's whole memory budget.
The worker also has restart policy `no`.

`SpeechService.synthesize()` retains small WAV byte strings for the current
part and joins them before returning. `run_batch()` keeps the same provider
and model alive across all parts. It does not accumulate the whole book's
audio in a Python list. At inspection, six completed WAVs totaled only
76,023,438 bytes, far smaller than the killed process's resident memory.

After restarting the worker, a live `/proc/1/status` sample showed:

```text
VmSize: 8845832 kB
VmHWM:  6196676 kB
VmRSS:  4979288 kB
VmSwap:       0 kB
Threads:     54
```

This establishes substantial runtime memory variability but is not a full
allocation trace. The exact mechanism—live tensor retention, CPU allocator
retention/fragmentation, or a generation-time peak—has not been distinguished.
Do not describe a specific Parler/PyTorch memory leak as proven.

## Recovery and remaining engineering work

The existing disk checkpoints preserved completed parts 1–6 and seven chunks
of part 7. The worker was already resumed before this deeper investigation;
it skipped the completed parts and reused the saved chunks. No runtime policy
or synthesis code was changed during this diagnosis.

A robust implementation should measure RSS and peak memory at every chunk,
bound the inference process's lifetime (for example, use a fresh process for
each part), and enforce a memory budget below the VM's total. Controlled
process recycling should reuse the existing chunk checkpoints and local model
cache. Automatic restart/resume can restore liveness after a kill, but does
not by itself cure memory growth. These are proposed follow-up changes, not
implemented or benchmarked fixes in this investigation.
