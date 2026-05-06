# Artsy upload gaps

- Works blocked from Artsy upload: **166**

## What's missing most often

| Missing field | Works |
|---|---:|
| medium | 120 |
| classification | 66 |
| image | 11 |
| title | 1 |

## Triage: closest to upload-ready first

Sorted by *number of missing fields ascending* — the smallest punch list at the top.

| KG-# | Missing | Title | Artist |
|---|---|---|---|
| KG-1019 | 1: medium | Jade-hilted and gilt khanjar |  |
| KG-1020 | 1: medium | Jade-hilted and jeweled khanjar |  |
| KG-1046 | 1: classification | Large pagoda of Tritchinapali |  |
| KG-1059 | 1: classification | Bas relief of the temple of Indra |  |
| KG-1069 | 1: medium | A Ram’s Head Shamshir |  |
| KG-1094 | 1: medium | Illustration from a Kama Sutra series |  |
| KG-1095 | 1: medium | Illustration from a Kama Sutra series |  |
| KG-1096 | 1: medium | Illustration from a Kama Sutra series |  |
| KG-1097 | 1: medium | Illustration from a Kama Sutra series |  |
| KG-1098 | 1: medium | Illustration from a Kama Sutra series |  |
| KG-1099 | 1: medium | Illustration from a Kama Sutra series |  |
| KG-1111 | 1: medium | Shiva, Parvati, and the Holy Family |  |
| KG-1112 | 1: medium | Holy Family |  |
| KG-1172 | 1: medium | Equestrian Portrait |  |
| KG-1178 | 1: medium | Sri Nathji |  |
| KG-1202 | 1: image | A Sikh Elder Holding Prayer Beads |  |
| KG-1220 | 1: medium | Portrait of a Flower Lady Making Garland |  |
| KG-1223 | 1: medium | Two Devotees |  |
| KG-1224 | 1: medium | Holy Man Praying |  |
| KG-1240 | 1: title |  |  |
| KG-1241 | 1: medium | Rao Saseb Vijai Singh Ji |  |
| KG-1242 | 1: medium | Portrait |  |
| KG-1261 | 1: medium | Two Persian Line Drawings A) Female Musician B) Nobleman wit |  |
| KG-1262 | 1: medium | Sad old guy |  |
| KG-1263 | 1: medium | Lovers |  |
| KG-1289 | 1: medium | Talwar engraved with images of the ten avatars of Vishnu |  |
| KG-1290 | 1: medium | Koftgari talwar |  |
| KG-1328 | 1: classification | See India, Mysore |  |
| KG-1336 | 1: medium | Car Festival at Puri, India |  |
| KG-1337 | 1: classification | Visit India, Sanchi |  |
| KG-1338 | 1: classification | Sanchi/Visit India |  |
| KG-1340 | 1: classification | Banaras, India |  |
| KG-1343 | 1: classification | India via Bank of America |  |
| KG-1345 | 1: classification | India, Fly Qantas |  |
| KG-1346 | 1: classification | Colorful Middle East |  |
| KG-1348 | 1: medium | Darjeeling and Kanchanjunga |  |
| KG-1349 | 1: classification | Banaras, See India |  |
| KG-1350 | 1: classification | Banaras, See India |  |
| KG-1351 | 1: medium | Udaipur, Visit India |  |
| KG-1352 | 1: classification | Udaipur, Visit India |  |
| KG-1355 | 1: medium | Visit India, Kashmir |  |
| KG-1357 | 1: medium | Ajanta; 2500th Buddha Jayanti, India, The Land of Buddha |  |
| KG-1360 | 1: medium | Golden Temple, Amritsar, India |  |
| KG-1361 | 1: medium | Meenakshi Temple, Madurai, India |  |
| KG-1376 | 1: classification | See India/Amber |  |
| KG-1377 | 1: classification | Visit India/A Street by Moonlight |  |
| KG-1378 | 1: classification | Mount Abu/Visit India |  |
| KG-1379 | 1: classification | See Ceylon |  |
| KG-1380 | 1: medium | Simla, See India |  |
| KG-1381 | 1: medium | Indian State Railways, Kashmir |  |

## Unresolved conflicts

Each row blocks confidence in the canonical value.
Resolve with: `python -m src.cli resolve <KG-#> <field> "<value>" --reason "..."`

| KG-# | Field | Distinct values | Sources |
|---|---|---|---|
| KG-1000 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1001 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1002 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1003 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1004 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1007 | classification | Object \| Sculpture | artsy_csv,match_workbook |
| KG-1011 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1012 | classification | Khanjar \| Design/Decorative Art | artsy_csv,match_workbook |
| KG-1013 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1015 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1312 | height_in | 13.0 \| 9.0 | artsy_csv |
| KG-1312 | medium | Ground mineral pigments on paper \| Opaque watercolor heightened with gold on paper | artsy_csv |
| KG-1312 | price_usd | 50000.0 \| 26000.0 | artsy_csv |
| KG-1312 | title | Battle between Banasura and Krishna \| Vasishtha Teaches Rama and Lakshmana | artsy_csv |
| KG-1312 | width_in | 20.0 \| 14.0 | artsy_csv |
| KG-1312 | year | 1775 \| 1700 | artsy_csv |
