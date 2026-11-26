# news-image-20261125

[![make.fun · news-image-20261125](https://make.fun/badge/news-image-20261125.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![rank](https://make.fun/badge/news-image-20261125/zurrrtzy-create/news-image-20261125/rank.svg)](https://make.fun/bounty/news-image-20261125/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![reward](https://make.fun/badge/news-image-20261125/zurrrtzy-create/news-image-20261125/reward.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)

A newspaper front page summing up the world news of Wednesday 25 November
2026: 30 stories, from two tankers hitting mines in the Strait of Hormuz
(Brent jumps to $91) to Washington proposing tariffs on 14 trading partners
(China faces an extra 20%) and the Nasdaq plunging 4% intraday as the AI
rout rattled Wall Street (Nvidia down 8.7% at one point, VIX at 35); plus
Shenzhou-24 docking at Tiangong with Pakistan's first astronaut, Ukraine
hitting five Russian warplanes at Savasleyka, the Houthi claim on Ras
Tanura, the Cairo tanker fire that killed 31, the Solomons–Australia
security treaty, Huawei's conviction, and 15 more stories — with a date
check box that honestly notes what was left out (the Huawei verdict is from
Tue 24 Nov and the heat record from Sun 22 Nov).

`main.py` (Python 3.13, standard library only) copies `entry.png` to
`/output/entry.png` (1024x1024, deterministic - two runs write identical
bytes). The image itself was rendered by `render.py` (Pillow + the real
EB Garamond and Playfair Display fonts in `fonts/`, SIL OFL). No network,
no randomness, no wall-clock time.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```
