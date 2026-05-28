# Artsy upload gaps

- Works blocked from Artsy upload: **928**

## What's missing most often

| Missing field | Works |
|---|---:|
| image | 887 |
| medium | 308 |
| classification | 277 |
| title | 4 |

## Triage: closest to upload-ready first

Sorted by *number of missing fields ascending* — the smallest punch list at the top.

| KG-# | Missing | Title | Artist |
|---|---|---|---|
| KG-1005 | 1: image | Untitled (Woman Standing) | Jamini Roy |
| KG-1018 | 1: image | Indian clay figures | Jadunath Pal |
| KG-1035 | 1: image | Thomas Daniell and Robert Havell - 3 engravings | Thomas Daniell |
| KG-1036 | 1: image | Illustration to the ‘Large’ Guler-Basohli Bhagavata Purana:  | Attributed to Manaku |
| KG-1037 | 1: image | Illustration to the ‘Large’ Guler-Basohli Bhagavata Purana:  | Attributed to First Generation after Nainsukh and Manaku |
| KG-1202 | 1: image | A Sikh Elder Holding Prayer Beads |  |
| KG-1240 | 1: title |  |  |
| KG-1241 | 1: medium | Rao Saseb Vijai Singh Ji |  |
| KG-1242 | 1: medium | Portrait |  |
| KG-1323 | 1: image | Fly TWA – The Orient | David Klein |
| KG-1324 | 1: image | India, Fly TWA | David Klein |
| KG-1325 | 1: image | Fly TWA - India | David Klein |
| KG-1326 | 1: image | Fly TWA - India | David Klein |
| KG-1336 | 1: medium | Car Festival at Puri, India |  |
| KG-1360 | 1: medium | Golden Temple, Amritsar, India |  |
| KG-1361 | 1: medium | Meenakshi Temple, Madurai, India |  |
| KG-1363 | 1: medium | India, Air India |  |
| KG-1367 | 1: medium | There is an Air about India, Air India |  |
| KG-1483 | 1: image | Man and woman near fire |  |
| KG-1509 | 1: medium | Need title |  |
| KG-1510 | 1: medium | Need title |  |
| KG-1541 | 1: image | 6 Botanical Studies of Tree Branches and Fruit |  |
| KG-1564 | 1: medium | 2 Leafs from a Jain Manuscript |  |
| KG-1577 | 1: image | Radha Berates Krishna for Going with Other Women | Attributed to Manaku |
| KG-1610 | 1: image | Figures seated in conversation | Attributed to Manaku |
| KG-1615 | 1: image | The Great Monkey Army Battles Indrajit (Leaf from the 'Secon | Attributed to First Generation after Nainsukh and Manaku |
| KG-1616 | 1: image | Shurpanakha Complains that her Nose was Cut off by Lakshman | Attributed to First Generation after Nainsukh and Manaku |
| KG-1620 | 1: image | Ganesha Enthroned | Attributed to First Generation after Nainsukh and Manaku |
| KG-1626 | 1: image | Vishnu |  |
| KG-1631 | 1: image | Lalita Maha Tripura Sundari | Attributed to Sajnu |
| KG-1650 | 1: classification | Makara Bangle (Makaranathi) |  |
| KG-1651 | 1: classification | Drawing Water from a Well |  |
| KG-1654 | 1: classification | Brahma |  |
| KG-1657 | 1: image | Vajravarahi |  |
| KG-1658 | 1: image | Buddha Shakyamuni |  |
| KG-1661 | 1: classification | King Ralpachen |  |
| KG-1664 | 1: classification | Arhat Bakula |  |
| KG-1666 | 1: image | Bodhisattva |  |
| KG-1667 | 1: classification | Vajrapani |  |
| KG-1669 | 1: classification | Hevajra |  |
| KG-1672 | 1: image | The Celestial Musician, Narada |  |
| KG-1674 | 1: image | Narasimha Disemboweling Hiranyakshapu |  |
| KG-1680 | 1: image | Chinnamasta | Nainsukh |
| KG-1681 | 1: image | A portrait of Mian Hadala Pal (1673- 1678) | Attributed to First Generation after Nainsukh |
| KG-1684 | 1: image | Rama and His Allies Take Counsel (Leaf from the ‘Second’ Gul | Attributed to First Generation after Nainsukh and Manaku |
| KG-1688 | 1: image | Radha and Krishna Gaze Into a Mirror |  |
| KG-1697 | 1: image | A carved sandstone Jina |  |
| KG-1699 | 1: image | Ganesh |  |
| KG-1700 | 1: image | A stone stele of Shiva and Parvati (Uma Maheshvara) |  |
| KG-1701 | 1: image | A black stone stele of Vishnu |  |

## Unresolved conflicts

Each row blocks confidence in the canonical value.
Resolve with: `python -m src.cli resolve <KG-#> <field> "<value>" --reason "..."`

| KG-# | Field | Distinct values | Sources |
|---|---|---|---|
| KG-1012 | classification | Design/Decorative Art \| Khanjar | artsy_csv,bulk_upload_xlsx,match_workbook |
| KG-1012 | medium | Jade-hilted and jeweled \| Jade-hilted and jeweled Khanjar | artsy_csv,bulk_upload_xlsx |
| KG-1093 | medium | Opaque watercolor on cloth \| Thangka -Opaque watercolor on cloth | artsy_csv,bulk_upload_xlsx |
| KG-1301 | medium | Opaque watercolor heightened with gold on paper
 Calligraphy panel on verso \| Opaque watercolor heightened with gold on paper  
Calligraphy panel on verso | artsy_csv,bulk_upload_xlsx |
| KG-1312 | height_in | 13.0 \| 9.0 | artsy_csv,bulk_upload_xlsx |
| KG-1312 | medium | Ground mineral pigments on paper \| Opaque watercolor heightened with gold on paper | artsy_csv,bulk_upload_xlsx |
| KG-1312 | price_usd | 26000.0 \| 50000.0 | artsy_csv,bulk_upload_xlsx |
| KG-1312 | title | Battle between Banasura and Krishna \| Vasishtha Teaches Rama and Lakshmana | artsy_csv,bulk_upload_xlsx |
| KG-1312 | width_in | 14.0 \| 20.0 | artsy_csv,bulk_upload_xlsx |
| KG-1312 | year | 1700 \| 1775 | artsy_csv,bulk_upload_xlsx |
| KG-1316 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1317 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1318 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1319 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1320 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1321 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1327 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1329 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1334 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1335 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1341 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1342 | classification | Posters \| Print | artsy_csv,bulk_upload_xlsx |
| KG-1344 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1347 | classification | Posters \| Print | artsy_csv,bulk_upload_xlsx |
| KG-1348 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1351 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1355 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1357 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1380 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
| KG-1381 | classification | Drawing, Collage or other Work on Paper \| Posters | artsy_csv,bulk_upload_xlsx |
