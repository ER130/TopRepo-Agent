# TopRepo source datasets: Phase 1 summary (v4: complete, with the all-species meta table)

Companion file: `toprepo_datasets_phase1.tsv`. It has one row per subdataset (112 rows) and a source tag on every value.

## 1. Sources, in order of authority

1. **toprepo.org combined meta table, `toprepo_meta_table_v1.2.1.tsv`** ("All" species view).
   * One row per raw file.
   * Columns used: Dissociation, Separation, Cysteine_protection, FAIMS.
2. **TopRepo supplement** (media-2.xlsx):
   * S1 publications, S3 projects, S5 subdatasets (species, sample, instrument, dissociation).
   * S6/S7 file lists, S11 TopFD and S13 TopPIC parameters.
3. **Original papers / repository records I read.** These are kept as context and cross-checks only.

Paper: Li K … Liu X, bioRxiv 2026, doi:10.64898/2026.02.20.707032, v2 (posted 2026-04-30).

### Integrity checks on the combined table

* **Size:** 3,165 rows, 87 datasets, 12 species. The species counts equal Fig. 1a/d exactly (Human 2,611, E. coli 175, Mouse 83, …).
* **Join to the repo file:** joined on (Dataset_id, MZML_file_name) to the repo's `toprepo_file_info_v1.2.1.tsv`.
  * 0 unmatched rows, 0 duplicate keys, 0 local files missing.
  * Every `#Msalign_files` value agrees.
* **Same values as the human-only file:** all 2,611 human rows are identical, field for field.
* **Dual-species accessions are split correctly.** Each of the three dual-species accessions resolves to one species per project.
* **Against S5, corpus-wide, only one disagreement:** P25's dissociation (see §4). Sample labels and instruments match S5 everywhere.

## 2. TopRepo's blanket processing parameters

**TopFD 1.7.10 [S11]:**

| Parameter | Value |
|---|---|
| Spectral data type | centroid |
| Max charge | 30 |
| Max mass | 70,000 Da |
| Peak error tolerance | 0.02 m/z |
| MS1 S/N | 3 |
| MS/MS S/N | 1 |
| Precursor window | 3 m/z |
| Final filtering | yes |

**TopPIC 1.7.11 [S13]:**

| Parameter | Value |
|---|---|
| Fragmentation method | from file |
| Precursor/fragment tolerance | 10 ppm |
| N-terminal forms | NONE, M_ACETYLATION, NME, NME_ACETYLATION |
| Unexpected mass shifts | 1, range −500 to +500 Da |
| PrSM FDR | 0.01 |
| Proteoform FDR | 0.01 |
| Cluster tolerance | 1.2 Da |
| Use TopFD features | yes |
| E-value | generating function |
| **Fixed mod** | **none or carbamidomethyl Cys, per dataset**, taken from the meta table's `Cysteine_protection` |

## 3. All 38 projects

Every column now comes from the meta table, except instrument [S5] and publication [S1].

| P | Accession(s) | Publication (S1) | Species · sample | Instrument | Dissociation | Separation | **Cys protection → `-f`** | FAIMS |
|---|---|---|---|---|---|---|---|---|
| 1 | PXD071282 | McCool Anal Chem 2018 | E. coli · E. coli K-12 MG1655 | Q Exactive HF | HCD | CZE | **Carbamidomethylation** → C57 | No |
| 2 | PXD017265 | Chen Anal Chem 2020 | Zebrafish · Zebrafish brain | Q Exactive HF | HCD | CZE | **Carbamidomethylation** → C57 | No |
| 3 | MSV000091610 | Kline Anal Chem 2023 | E. coli · E. coli K-12 25922 | Orbitrap Eclipse | HCD | RPLC | **None** → none | mixed |
| 4 | MSV000080257 | Park Nat Methods 2017 | Human · Ovarian cancer tumor tissue | LTQ Orbitrap Elite | CID | RPLC | **None** → none | No |
| 5 | PXD034368 | Li Proteomics 2023 | A. thaliana · 2 sample types | Q Exactive HF | HCD | CZE | **Carbamidomethylation** → C57 | No |
| 6 | MSV000093727 | Fulcher Mol Cell Proteomics 2025 | Mouse · Brain tissue (WT C57BL/6 J) | Orbitrap Fusion Lumos | CID | RPLC | **None** → none | Yes |
| 7 | PXD017265 | Chen Anal Chem 2020 | E. coli · E. coli K-12 MG1655 | Q Exactive HF | HCD | CZE | **Carbamidomethylation** → C57 | No |
| 8 | PXD027741 | Lubeckyj Mol Omics 2022 | Zebrafish · Zebrafish brain | Q Exactive HF | HCD | CZE | **None** → none | No |
| 9 | PXD029703 | McCool Sci Adv 2022 | Human · 2 sample types | Q Exactive HF | HCD | CZE | **Carbamidomethylation** → C57 | No |
| 10 | MSV000088565 | Drown J Proteome Res 2022 | Human · 5 sample types | Orbitrap Eclipse / Orbitrap Fusion Lumos | HCD | RPLC / CZE | **None** → none | No |
| 11 | MSV000093728 | Fulcher Mol Cell Proteomics 2025 | Human · Brain frontal gyrus tissue | Orbitrap Fusion Lumos | CID | RPLC | **None** → none | Yes |
| 12 | PXD046651 | Sadeghi J Proteome Res 2024 | Yeast · Yeast S288c | Q Exactive HF | HCD | CZE | **None** → none | No |
| 13 | MSV000092097 | Fulcher Endocrinology 2023 | Mouse · Mouse pancreatic islet (pancrea beta cells) | Orbitrap Fusion Lumos | CID | RPLC | **Carbamidomethylation** → C57 | Yes |
| 14 | PXD038038 | Melo Sci Rep 2023 | C. glutamicum · C. glutamicum ATCC 13032 | LTQ Orbitrap Elite | HCD | RPLC | **None** → none | No |
| 15 | PXD035339 | Johnson Anal Chem 2022 | Human · 2 sample types | Orbitrap Fusion Lumos | HCD | CZE | **None** → none | No |
| 16 | PXD018248 | Yang J Proteome Res 2020 | Human · HepG2 cells | Q Exactive HF | HCD | CZE | **None** → none | No |
| 17 | PXD029792 | Kaulich Anal Chem 2022 | Human · CaCo-2 Caucasian colon cancer cells | Orbitrap Fusion Lumos | CID | RPLC | **None** → none | mixed |
| 18 | MSV000086696 | Fulcher J Proteome Res 2021 | Human · Brain midfrontal cortex tissue | Orbitrap Fusion Lumos | CID | RPLC | **None** → none | mixed |
| 19 | MSV000085978 | Schaffer J Proteome Res 2021 | Human · MCF-7 breast cancer cells | FT-ICR (LTQ FT Ultra) | CID | RPLC | **None** → none | No |
| 20 | PXD049969 | Kaulich Nat Methods 2024 | Human · CaCo-2 Caucasian colon cancer cells | Orbitrap Fusion Lumos | CID | RPLC | **None (124 files); Carbamidomethylation (3 files)** → MIXED - set per raw file | Yes |
| 21 | PXD034353 | Takemori Anal Chem 2022 | Human · K562 lymphoblast cells | Orbitrap Fusion Lumos | CID | RPLC | **Carbamidomethylation** → C57 | Yes |
| 22 | PXD018248 | Yang J Proteome Res 2020 | E. coli · E. coli K-12 MG1655 | Q Exactive HF | HCD | CZE | **None** → none | No |
| 23 | 54 accessions | Melani Science 2022 | Human · 23 sample types | FT-ICR / Elite / Lumos | CID / ETD / HCD | RPLC | **None** → none | No / Yes |
| 24 | MSV000089163 | Liao Mol Cell Proteomics 2023 | Human · HEK 293 Embryonic kidney cells | Orbitrap Fusion Lumos | HCD | RPLC | **None** → none | No |
| 25 | MSV000079978 | Anderson J Proteome Res 2016 | Human · DLD-1 parental (KRas wt/G13D) colorectal cancer cells | FT-ICR (LTQ FT Ultra) | CID (24 files); ETD (16 files) | RPLC | **None** → none | No |
| 26 | IPX0005864000 | Sun Anal Chem 2023 | Mouse · Brain hippocampus | Orbitrap Fusion Lumos | HCD | RPLC | **None** → none | No |
| 27 | MSV000089984 | Zhou Front Anal Sci 2022 | Glycine max · Glycine max (soybean) root nodules | Q Exactive HF | HCD | RPLC | **None** → none | No |
| 28 | IPX0005864000 | Sun Anal Chem 2023 | Human · HeLa cervical cancer cells | Orbitrap Fusion Lumos | HCD | RPLC | **None** → none | No |
| 29 | MSV000084612 | Zhou Anal Chem 2020 | Human · HeLa cervical cancer cells | Orbitrap Fusion Lumos | HCD | RPLC | **None** → none | No |
| 30 | MSV000079913 | Fornelli J Proteome Res 2016 | Human · IMR90 fibroblast cells | Q Exactive | HCD | RPLC | **None** → none | No |
| 31 | MSV000085258 | Takemori J Proteome Res 2020 | E. coli · E. coli K-12 MG1655 | FT-ICR (LTQ FT Ultra) | CID | RPLC | **Carbamidomethylation** → C57 | No |
| 32 | PXD051505 | Ramirez-Sagredo Clin Proteomics 2024 | Mouse · Heart tissue | Orbitrap Exploris 240 | HCD | RPLC | **Carbamidomethylation** → C57 | No |
| 33 | PXD042298 | Wang Anal Chem 2023 | Mouse · Brain | Q Exactive HF | HCD | CZE | **None** → none | No |
| 34 | PXD039883 | Leipert Angew Chem Int Ed Engl 2023 | Caenorhabditis elegans · C. elegans nematodes | Orbitrap Fusion Lumos | CID | RPLC | **None** → none | mixed |
| 35 | MSV000089163 | Liao Mol Cell Proteomics 2023 | Rat · Female brain | Orbitrap Fusion Lumos / Orbitrap Eclipse | HCD | RPLC | **None** → none | No / Yes |
| 36 | MSV000092574 | Kline J Proteome Res 2023 | Human · Serum | Orbitrap Eclipse | HCD | RPLC | **None** → none | mixed |
| 37 | PXD041979 | Genth Microbiol Spectr 2023 | Blautia producta · Blautia producta strain DSM 2950 | Orbitrap Fusion Lumos | CID | RPLC | **None** → none | Yes |
| 38 | PXD019792 | Cassidy J Proteomics 2021 | Methanosarcina mazei · Archaea Methanosarcina mazei | Orbitrap Fusion Lumos | HCD / EThcD | RPLC | **None** → none | No |

**Fixed-mod summary (`toppic -f`):**

* **Carbamidomethylation → C57 (9 projects): P1, P2, P5, P7, P9, P13, P21, P31, P32.**
* **None → no `-f` (28 projects):** everything else, except P20.
* **Mixed (P20 / PXD049969).** The three `20230917_Caco_1DLC_alkylated_R{1,2,3}_LMW.raw` files are Carbamidomethylation; the other 124 files are None. This must be set per raw file, never per project.

## 4. Checks against what I read in the original papers

**The three predictions:**

| Prediction | Meta table | Result |
|---|---|---|
| P31 = Carbamidomethylation (Takemori 2020: 1 mM DTT + 2 mM iodoacetamide) | Carbamidomethylation | ✅ |
| P32 = Carbamidomethylation (Ramirez-Sagredo 2024: TCEP + ~20 mM IAA, fixed Cys mod) | Carbamidomethylation | ✅ |
| P8 = None (Lubeckyj 2022: OG lysis, no reduction/alkylation) | None | ✅ |

**Every other project where I had read the paper or record:**

| Project | What the source said | Meta table | Result |
|---|---|---|---|
| P6 | TCEP, alkylation not mentioned | None | ✅ consistent |
| P7 | "denatured, reduced and alkylated", reagent not named | Carbamidomethylation | ✅ consistent; the meta table supplies the reagent |
| P16, P22 | Reduction/alkylation not reported | None | ✅ consistent |
| P18 | TCEP, no alkylation | None | ✅ |
| P19 | DTT, alkylation not reported | None | ✅ consistent |
| P12, P27 | Not reported for top-down | None | ✅ consistent |
| **P2** (zebrafish, Chen 2020) | Not reported; zebrafish data **re-used from an earlier study** I haven't read | **Carbamidomethylation** | ⚠️ unverified, not a conflict |

* **No direct contradictions.** Every case where a paper explicitly states alkylation or its absence agrees with the meta table.
* **The only soft spot is P2.** It's the only C57 value I couldn't trace to a statement in a paper. If it matters, the earlier zebrafish CZE study by the same lab would be the place to confirm. P2 is 1 raw file, so the impact is small.

**Dissociation:**

* **P25:** the meta table says 24 CID + 16 ETD, and S5 says CID for all 40. The meta table matches the file names exactly. **S5 is wrong here.** This is the only S5 disagreement in the whole corpus.
* **P17:** the meta table agrees with S5 (all CID). It remains low priority: the 3 ambiguous file names contain both "CID25" and "HCD30".
* **P38 subdataset 108:** EThcD in both sources. Upstream TopRepo's `fix_ethcd_activation.py` exists because these scans can be labelled `ACTIVATION=ETD` inside msalign files.

**Still unresolved:**

* **P3's sample label** is "E. coli K-12 25922" in both S5 and the meta table. They share the same curation, so this can't be resolved from these files. ATCC 25922 is not a K-12 strain; Kline 2023 would settle it.
* This doesn't affect the database (UniProt UP000000625, K-12) or any parameter, so it's low priority.

## 5. Patterns worth carrying into Phase 2

* **Alkylation is the minority.** About 19% of raw files (601 of 3,165) are carbamidomethylated, and 28 of 38 projects use no fixed mod. A precedent lookup should therefore **not default to C57**. The skills should ask whether the sample was alkylated, and fall back to the closest precedent only if the user doesn't know.
* **Lab is not a reliable proxy.** The same group (Sun lab, CZE) has both C57 projects (P1, P2, P5, P7, P9) and None projects (P8, P12, P16, P22, P33).
* **Separation:**
  * CZE: P1, 2, 5, 7, 8, 9, 12, 15, 16, 22, 33, and P10's CZE subdatasets (38, 39, 41).
  * RPLC: everything else.
* **Dissociation:** CID/HCD dominate. ETD is 53 files (P23, P25) and EThcD is 19 files (P38). Both matter for TD-Pred, which was trained only on HCD/CID.
* **FAIMS:**
  * The meta table flags 868 raw files, including single-CV runs.
  * Several projects mix FAIMS and no-FAIMS files: P3 (24/24), P17, P18, P23, P34 (53/4), P35, P36.
  * So FAIMS should also be decided per raw file, not per project.

Phase 1 is complete: all 38 projects and 112 subdatasets have every field filled from TopRepo's own metadata. I haven't touched the repo.
