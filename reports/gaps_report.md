# Artsy upload gaps

- Works blocked from Artsy upload: **824**

## What's missing most often

| Missing field | Works |
|---|---:|
| classification | 777 |
| image | 774 |
| medium | 251 |
| title | 4 |

## Triage: closest to upload-ready first

Sorted by *number of missing fields ascending* — the smallest punch list at the top.

| KG-# | Missing | Title | Artist |
|---|---|---|---|
| KG-1024 | 1: classification | Bon Thangka of Satrig Ersang |  |
| KG-1032 | 1: classification | Panchamukhalinga |  |
| KG-1088 | 1: classification | A gray schist figure of Buddha |  |
| KG-1114 | 1: classification | Architrave |  |
| KG-1202 | 1: image | A Sikh Elder Holding Prayer Beads |  |
| KG-1240 | 1: title |  |  |
| KG-1291 | 1: classification | Gandharan Head |  |
| KG-1336 | 1: medium | Car Festival at Puri, India |  |
| KG-1340 | 1: classification | Banaras, India |  |
| KG-1363 | 1: medium | India, Air India |  |
| KG-1367 | 1: medium | There is an Air about India, Air India |  |
| KG-1383 | 1: classification | Kashmir / Indian Railways |  |
| KG-1384 | 1: classification | Kashmir |  |
| KG-1385 | 1: classification | East Indian Railway, Banaras |  |
| KG-1386 | 1: classification | India / The Wonderful Land |  |
| KG-1399 | 1: classification | Megha Raga |  |
| KG-1541 | 1: image | 6 Botanical Studies of Tree Branches and Fruit |  |
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
| KG-1667 | 1: classification | Vajrapani |  |
| KG-1669 | 1: classification | Hevajra |  |
| KG-1672 | 1: image | The Celestial Musician, Narada |  |
| KG-1674 | 1: image | Narasimha Disemboweling Hiranyakshapu |  |
| KG-1688 | 1: image | Radha and Krishna Gaze Into a Mirror |  |
| KG-1697 | 1: image | A carved sandstone Jina |  |
| KG-1718 | 1: image | Abhayakaragupta |  |
| KG-1720 | 1: image | Four-armed Mahakala with Consort |  |
| KG-1737 | 1: image | Shakyamuni |  |
| KG-1738 | 1: image | The Elder Arhat Kanakavatsa |  |
| KG-1739 | 1: image | Chakrasamvara and Consort |  |
| KG-1741 | 1: image | Vajrapani, Hayagriva, Garuda combined |  |
| KG-1794 | 1: image | Mahakala |  |
| KG-1802 | 1: image | Sarvabuddha Dakini with Dancing Citipati |  |
| KG-1803 | 1: image | Vairocana |  |
| KG-1804 | 1: image | Seventh Dalai Lama |  |
| KG-1806 | 1: image | Jain Cosmological Diagram |  |
| KG-1812 | 1: image | A Mandala Depicting Vajrabhairava |  |
| KG-1813 | 1: image | Large Thangka White Tara Tibetan |  |
| KG-1814 | 1: image | Dipankara Buddha with Arhats Deities Thangka |  |
| KG-1816 | 1: image | Green Tara with Monks and Deities Thangka |  |
| KG-2106 | 1: image | Tibetan Thangka depicting Saddha (Milarepa) |  |

## Unresolved conflicts

Each row blocks confidence in the canonical value.
Resolve with: `python -m src.cli resolve <KG-#> <field> "<value>" --reason "..."`

| KG-# | Field | Distinct values | Sources |
|---|---|---|---|
| KG-1000 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1000 | medium | Opaque Watercolor on Paper \| Drawing \|  Collage or other Work on Paper | artsy_csv,bulk_upload_xlsx |
| KG-1000 | width_in | 11.125 \| 11125.0 | artsy_csv,bulk_upload_xlsx |
| KG-1001 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1001 | medium | Opaque watercolor heightened with gold on paper \| Drawing \|  Collage or other Work on Paper | artsy_csv,bulk_upload_xlsx |
| KG-1002 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1002 | medium | Gouache and gold on paper \| Drawing \|  Collage or other Work on Paper | artsy_csv,bulk_upload_xlsx |
| KG-1003 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1003 | medium | Opaque watercolor heightened with gold on paper \| Drawing \|  Collage or other Work on Paper | artsy_csv,bulk_upload_xlsx |
| KG-1004 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1004 | medium | Opaque watercolor heightened with gold on paper \| Drawing \|  Collage or other Work on Paper | artsy_csv,bulk_upload_xlsx |
| KG-1006 | medium | Sandstone \| Sculpture | artsy_csv,bulk_upload_xlsx |
| KG-1007 | classification | Object \| Sculpture | artsy_csv,match_workbook |
| KG-1007 | medium | Stucco \| Sculpture | artsy_csv,bulk_upload_xlsx |
| KG-1008 | medium | Gray Schist \| Sculpture | artsy_csv,bulk_upload_xlsx |
| KG-1009 | medium | Blue Grey Schist \| Sculpture | artsy_csv,bulk_upload_xlsx |
| KG-1010 | medium | Schist \| Sculpture | artsy_csv,bulk_upload_xlsx |
| KG-1011 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1011 | medium | Watercolor on Whatman paper \| Drawing \|  Collage or other Work on Paper | artsy_csv,bulk_upload_xlsx |
| KG-1012 | classification | Khanjar \| Design/Decorative Art | artsy_csv,match_workbook |
| KG-1012 | medium | Jade-hilted and jeweled \| Design/Decorative Art | artsy_csv,bulk_upload_xlsx |
| KG-1013 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1013 | medium | Opaque watercolor heightened with gold on paper \| Drawing \|  Collage or other Work on Paper | artsy_csv,bulk_upload_xlsx |
| KG-1014 | medium | Bronze with polychrome \| Sculpture | artsy_csv,bulk_upload_xlsx |
| KG-1015 | classification | Painting \| Drawing \|  Collage or other Work on Paper | artsy_csv,match_workbook |
| KG-1015 | medium | Opaque watercolor heightened with gold on paper \| Drawing \|  Collage or other Work on Paper | artsy_csv,bulk_upload_xlsx |
| KG-1016 | medium | Schist \| Sculpture | artsy_csv,bulk_upload_xlsx |
| KG-1017 | medium | Green Schist \| Sculpture | artsy_csv,bulk_upload_xlsx |
| KG-1021 | medium | Opaque watercolor heightened with gold on paper \| Painting | artsy_csv,bulk_upload_xlsx |
| KG-1022 | medium | Opaque watercolor heightened with gold on paper \| Drawing \|  Collage or other Work on Paper | artsy_csv,bulk_upload_xlsx |
