# Results  (alpha=25.0, key='demo-secret-key', image 3000x2000, ~22.9 copies/bit)

Null-score threshold (mean+6sd over 126 trials): 0.0966  (null max 0.0870)

| Attack | Method | NC | BER | score | detected | grid(x,y) | phase |
|---|---|---|---|---|---|---|---|
| none | dct | 1.000 | 0.000 | 0.996 | yes | (0, 0) | (0, 0) |
| none | lsb | 1.000 | 0.000 | 0.996 | yes | (0, 0) | (0, 0) |
| JPEG Q=90 | dct | 1.000 | 0.000 | 0.994 | yes | (0, 0) | (0, 0) |
| JPEG Q=90 | lsb | 0.107 | 0.447 | 0.075 | no | (5, 0) | (47, 58) |
| JPEG Q=70 | dct | 1.000 | 0.000 | 0.935 | yes | (0, 0) | (0, 0) |
| JPEG Q=70 | lsb | 0.113 | 0.444 | 0.069 | no | (6, 2) | (16, 17) |
| JPEG Q=50 | dct | 0.910 | 0.045 | 0.773 | yes | (0, 0) | (0, 0) |
| JPEG Q=50 | lsb | 0.122 | 0.439 | 0.068 | no | (1, 6) | (29, 24) |
| JPEG Q=30 | dct | 0.373 | 0.314 | 0.469 | yes | (0, 0) | (0, 0) |
| JPEG Q=30 | lsb | 0.077 | 0.462 | 0.074 | no | (4, 6) | (32, 24) |
| noise s=3 | dct | 1.000 | 0.000 | 0.995 | yes | (0, 0) | (0, 0) |
| noise s=3 | lsb | 0.112 | 0.444 | 0.070 | no | (0, 1) | (6, 53) |
| crop 2048x2000 (~64000 blk) | dct | 1.000 | 0.000 | 0.996 | yes | (3, 0) | (0, 49) |
| crop 2048x2000 (~64000 blk) | lsb | 1.000 | 0.000 | 0.996 | yes | (3, 0) | (0, 49) |
| crop 1024x1024 (~16384 blk) | dct | 1.000 | 0.000 | 0.994 | yes | (3, 5) | (13, 42) |
| crop 1024x1024 (~16384 blk) | lsb | 1.000 | 0.000 | 0.995 | yes | (3, 5) | (13, 42) |
| crop 1024x1024 + JPEG70 | dct | 0.998 | 0.001 | 0.929 | yes | (3, 5) | (13, 42) |
| crop 1024x1024 + JPEG70 | lsb | 0.161 | 0.420 | 0.076 | no | (5, 6) | (1, 48) |
| crop 640x640 (~6400 blk) | dct | 1.000 | 0.000 | 0.881 | yes | (3, 1) | (25, 43) |
| crop 640x640 (~6400 blk) | lsb | 1.000 | 0.000 | 0.887 | yes | (3, 1) | (25, 43) |
| crop 640x640 + JPEG70 | dct | 0.960 | 0.020 | 0.762 | yes | (3, 1) | (25, 43) |
| crop 640x640 + JPEG70 | lsb | 0.100 | 0.450 | 0.070 | no | (1, 4) | (25, 29) |
| crop 512x512 (~4096 blk) | dct | 0.980 | 0.010 | 0.980 | yes | (1, 5) | (17, 4) |
| crop 512x512 (~4096 blk) | lsb | 0.979 | 0.010 | 0.981 | yes | (1, 5) | (17, 4) |
| crop 384x384 (~2304 blk) | dct | 0.676 | 0.162 | 0.706 | yes | (3, 1) | (46, 19) |
| crop 384x384 (~2304 blk) | lsb | 0.676 | 0.162 | 0.717 | yes | (3, 1) | (46, 19) |

Image quality of watermarked image vs original:

- dct: PSNR = 39.64 dB, SSIM = 0.9754
- lsb: PSNR = 63.71 dB, SSIM = 1.0000

Wrong key on JPEG Q=90 image: NC = 0.063, BER = 0.469, score = 0.0678

Overwrite attack (random bits, alpha=25): PSNR vs watermarked = 37.98 dB, NC = 0.088, BER = 0.456, score = 0.0965, detected = no
