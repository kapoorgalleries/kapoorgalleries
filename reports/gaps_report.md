# Artsy upload gaps

- Works blocked from Artsy upload: **84**

## What's missing most often

| Missing field | Works |
|---|---:|
| classification | 57 |
| medium | 43 |
| image | 11 |
| title | 1 |

## Triage: closest to upload-ready first

Sorted by *number of missing fields ascending* — the smallest punch list at the top.

| KG-# | Missing | Title | Artist |
|---|---|---|---|
| KG-1046 | 1: classification | Large pagoda of Tritchinapali |  |
| KG-1059 | 1: classification | Bas relief of the temple of Indra |  |
| KG-1202 | 1: image | A Sikh Elder Holding Prayer Beads |  |
| KG-1240 | 1: title |  |  |
| KG-1241 | 1: medium | Rao Saseb Vijai Singh Ji |  |
| KG-1242 | 1: medium | Portrait |  |
| KG-1328 | 1: classification | See India, Mysore |  |
| KG-1336 | 1: medium | Car Festival at Puri, India |  |
| KG-1340 | 1: classification | Banaras, India |  |
| KG-1343 | 1: classification | India via Bank of America |  |
| KG-1345 | 1: classification | India, Fly Qantas |  |
| KG-1346 | 1: classification | Colorful Middle East |  |
| KG-1348 | 1: medium | Darjeeling and Kanchanjunga |  |
| KG-1349 | 1: classification | Banaras, See India |  |
| KG-1350 | 1: classification | Banaras, See India |  |
| KG-1357 | 1: medium | Ajanta; 2500th Buddha Jayanti, India, The Land of Buddha |  |
| KG-1360 | 1: medium | Golden Temple, Amritsar, India |  |
| KG-1361 | 1: medium | Meenakshi Temple, Madurai, India |  |
| KG-1363 | 1: medium | India, Air India |  |
| KG-1367 | 1: medium | There is an Air about India, Air India |  |
| KG-1376 | 1: classification | See India/Amber |  |
| KG-1379 | 1: classification | See Ceylon |  |
| KG-1380 | 1: medium | Simla, See India |  |
| KG-1381 | 1: medium | Indian State Railways, Kashmir |  |
| KG-1383 | 1: classification | Kashmir / Indian Railways |  |
| KG-1384 | 1: classification | Kashmir |  |
| KG-1385 | 1: classification | East Indian Railway, Banaras |  |
| KG-1386 | 1: classification | India / The Wonderful Land |  |
| KG-1395 | 1: classification | India–In War and Peace |  |
| KG-1399 | 1: classification | Megha Raga |  |
| KG-1407 | 1: medium | Illuminated Horoscope Manuscript |  |
| KG-1408 | 1: medium | Book 2 |  |
| KG-1409 | 1: medium | Book 3 |  |
| KG-1509 | 1: medium | Need title |  |
| KG-1510 | 1: medium | Need title |  |
| KG-1513 | 1: medium | Thangka |  |
| KG-1541 | 1: image | 6 Botanical Studies of Tree Branches and Fruit |  |
| KG-1564 | 1: medium | 2 Leafs from a Jain Manuscript |  |
| KG-1600 | 1: medium | Book of Company Period Architectural Drawings |  |
| KG-1625 | 1: classification | Shiva and Parvati (Uma Maheshvara) |  |
| KG-1645 | 1: classification | Bahubali |  |
| KG-1647 | 1: classification | A Digambara Jina |  |
| KG-1650 | 1: classification | Makara Bangle (Makaranathi) |  |
| KG-1651 | 1: classification | Drawing Water from a Well |  |
| KG-1654 | 1: classification | Brahma |  |
| KG-1655 | 1: classification | Shiva Vinadhara |  |
| KG-1657 | 1: image | Vajravarahi |  |
| KG-1659 | 1: classification | Crowned Buddha |  |
| KG-1661 | 1: classification | King Ralpachen |  |
| KG-1664 | 1: classification | Arhat Bakula |  |

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
