# Artsy upload gaps

- Works blocked from Artsy upload: **891**

## What's missing most often

| Missing field | Works |
|---|---:|
| image | 887 |
| medium | 232 |
| classification | 206 |
| title | 4 |

## Triage: closest to upload-ready first

Sorted by *number of missing fields ascending* — the smallest punch list at the top.

| KG-# | Missing | Title | Artist |
|---|---|---|---|
| KG-0012 | 1: image | A Thangka of Palden Lhamo, 19th century |  |
| KG-1005 | 1: image | Untitled (Woman Standing) | Jamini Roy |
| KG-1018 | 1: image | Indian clay figures | Jadunath Pal |
| KG-1035 | 1: image | Thomas Daniell and Robert Havell - 3 engravings | Thomas Daniell |
| KG-1036 | 1: image | Illustration to the ‘Large’ Guler-Basohli Bhagavata Purana:  | Attributed to Manaku |
| KG-1037 | 1: image | Illustration to the ‘Large’ Guler-Basohli Bhagavata Purana:  | Attributed to First Generation after Nainsukh and Manaku |
| KG-1202 | 1: image | A Sikh Elder Holding Prayer Beads |  |
| KG-1240 | 1: title |  |  |
| KG-1323 | 1: image | Fly TWA – The Orient | David Klein |
| KG-1324 | 1: image | India, Fly TWA | David Klein |
| KG-1325 | 1: image | Fly TWA - India | David Klein |
| KG-1326 | 1: image | Fly TWA - India | David Klein |
| KG-1365 | 1: image | India, Air France | Georges Mathieu |
| KG-1483 | 1: image | Man and woman near fire |  |
| KG-1509 | 1: medium | Need title |  |
| KG-1510 | 1: medium | Need title |  |
| KG-1541 | 1: image | 6 Botanical Studies of Tree Branches and Fruit |  |
| KG-1577 | 1: image | Radha Berates Krishna for Going with Other Women | Attributed to Manaku |
| KG-1610 | 1: image | Figures seated in conversation | Attributed to Manaku |
| KG-1615 | 1: image | The Great Monkey Army Battles Indrajit (Leaf from the 'Secon | Attributed to First Generation after Nainsukh and Manaku |
| KG-1616 | 1: image | Shurpanakha Complains that her Nose was Cut off by Lakshman | Attributed to First Generation after Nainsukh and Manaku |
| KG-1620 | 1: image | Ganesha Enthroned | Attributed to First Generation after Nainsukh and Manaku |
| KG-1626 | 1: image | Vishnu |  |
| KG-1631 | 1: image | Lalita Maha Tripura Sundari | Attributed to Sajnu |
| KG-1657 | 1: image | Vajravarahi |  |
| KG-1658 | 1: image | Buddha Shakyamuni |  |
| KG-1666 | 1: image | Bodhisattva |  |
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
| KG-1702 | 1: image | A silver-inlaid bronze figure of Ganesha |  |
| KG-1703 | 1: image | A bronze figure of a female retinue figure |  |
| KG-1704 | 1: image | A bronze figure of Manjushri or Avalokiteshvara |  |
| KG-1705 | 1: image | A bronze figure of Skanda |  |
| KG-1707 | 1: image | A bronze figure of the goddess Meenakshi |  |
| KG-1708 | 1: image | A bronze figure of Parvati |  |
| KG-1709 | 1: image | A bronze figure of Durga |  |
| KG-1710 | 1: image | Shrine of Tirthankara Anantanatha |  |
| KG-1711 | 1: image | A bronze figure of Ganesha |  |
| KG-1712 | 1: image | A gilt-bronze figure of Nandi |  |
| KG-1713 | 1: image | A gilt-bronze figure of Kala Bhairava |  |
| KG-1714 | 1: image | A silver figure of Vajrapani |  |
| KG-1715 | 1: image | Buddha Shakyamuni and the Thirty-five Buddhas of Confession |  |

## Unresolved conflicts

Each row blocks confidence in the canonical value.
Resolve with: `python -m src.cli resolve <KG-#> <field> "<value>" --reason "..."`

| KG-# | Field | Distinct values | Sources |
|---|---|---|---|
| KG-1312 | height_in | 13.0 \| 9.0 | artsy_csv,bulk_upload_xlsx |
| KG-1312 | medium | Ground mineral pigments on paper \| Opaque watercolor heightened with gold on paper | artsy_csv,bulk_upload_xlsx |
| KG-1312 | price_usd | 26000.0 \| 50000.0 | artsy_csv,bulk_upload_xlsx |
| KG-1312 | title | Battle between Banasura and Krishna \| Vasishtha Teaches Rama and Lakshmana | artsy_csv,bulk_upload_xlsx |
| KG-1312 | width_in | 14.0 \| 20.0 | artsy_csv,bulk_upload_xlsx |
| KG-1312 | year | 1700 \| 1775 | artsy_csv,bulk_upload_xlsx |
| KG-1813 | price_usd | 24000.0 \| 38000.0 | bulk_upload_xlsx,price_list_pdf |
| KG-1814 | price_usd | 24000.0 \| 28000.0 | bulk_upload_xlsx,price_list_pdf |
| KG-2106 | height_in | 27.0 \| 27.125 | bulk_upload_xlsx,price_list_pdf |
| KG-2106 | price_usd | 30000.0 \| 80000.0 | bulk_upload_xlsx,price_list_pdf |
| KG-2106 | width_in | 39.0 \| 39.5 | bulk_upload_xlsx,price_list_pdf |
| KG-2224 | price_usd | 38000.0 \| 48000.0 | bulk_upload_xlsx,price_list_pdf |
| KG-2224 | width_in | 18.0 \| 18.25 | bulk_upload_xlsx,price_list_pdf |
| KG-2375 | height_in | 19.0 \| 19.5 | bulk_upload_xlsx,price_list_pdf |
| KG-2375 | price_usd | 18000.0 \| 25000.0 | bulk_upload_xlsx,price_list_pdf |
| KG-2375 | width_in | 13.0 \| 13.75 | bulk_upload_xlsx,price_list_pdf |
