import openpyxl, csv, collections, sys
wb=openpyxl.load_workbook(sys.argv[1],read_only=True,data_only=False)
R=lambda n:[r for r in wb[n].iter_rows(values_only=True)]
cl=lambda v: '' if v is None else str(v).replace('\t',' ').strip()
S1={r[0]:r for r in R('Table S1')[2:] if isinstance(r[0],int)}
S3={r[0]:r for r in R('Table S3')[2:] if isinstance(r[0],int)}
S5=[r for r in R('Table S5')[2:] if isinstance(r[0],int)]
S6=[r for r in R('Table S6')[2:] if r[0] and r[2]]
ms=collections.defaultdict(list)
for r in S6: ms[r[2]].append(r[4])
loc=list(csv.DictReader(open(sys.argv[3]),delimiter='\t'))
key={(x['DATASET id'],x['MZML file name']):int(x['SUBDATASET id']) for x in loc}
META=collections.defaultdict(lambda: collections.defaultdict(collections.Counter)); metasrc={}
for f in sys.argv[4:]:
    for x in csv.DictReader(open(f),delimiter='\t'):
        sd=key[(x['Dataset_id'],x['MZML_file_name'])]
        for c in ['Dissociation','Separation','Cysteine_protection','FAIMS']: META[sd][c][x[c].strip()]+=1
        metasrc[sd]=f.split('/')[-1]
def mfmt(sd,c):
    if sd not in META: return ''
    d=META[sd][c]
    return d.most_common(1)[0][0] if len(d)==1 else '; '.join(f"{k} ({v} files)" for k,v in d.most_common())
NR="not reported in source read"; NOT="original paper not read yet"
# Facts from original papers / repository records actually read (source tag in brackets)
O={
 2:dict(sep="CZE, 1.5 m LPA capillary, BGE 10% acetic acid [O: Chen 2020]",cys=NR+" (zebrafish data re-used from earlier study) [O: Chen 2020]",orig="TopPIC 1.2.6; 0.1% PrSM / 0.5% proteoform FDR [O: Chen 2020]"),
 7:dict(sep="CZE, 103 cm LPA capillary; BGE 5% AA / 20% AA / 20% AA+10% IPA+15% DMA [O: Chen 2020]",cys="'denatured, reduced and alkylated' - reagents not named [O: Chen 2020]",orig="TopPIC 1.2.6; 0.1% PrSM / 0.5% proteoform FDR [O: Chen 2020]"),
 8:dict(sep="CZE, dynamic pH junction, 75 cm LPA capillary, BGE 10% AA [O: Lubeckyj 2022]",cys="none: OG lysis, no reduction/alkylation [O: Lubeckyj 2022]",orig="TopPIC 1.4.0; 15 ppm; <=2 unexpected mods <=500 Da; 1% PrSM / 5% proteoform FDR; HCD NCE 20% [O: Lubeckyj 2022]"),
 9:dict(sep="SEC / RPLC / 2D SEC-RPLC fractionation, then CZE [O: McCool preprint]",cys=NR+" (methods in SI) [O: McCool preprint]",orig="TopPIC 1.4.0; 1% proteoform FDR [O: McCool preprint]"),
 12:dict(sep="CZE, 1 m LPA capillary [O: reuse paper, bioRxiv 2025.02.05.636727]",cys=NR,orig="(reuse paper) TopPIC 1.7.6, 1% FDR"),
 16:dict(sep="CZE, LPA capillary, BGE 40% AA [O: Yang 2020]",cys="1% SDS lysis; reduction/alkylation not reported [O: Yang 2020]",orig="TopPIC 1.3.1, max 1 mass shift, defaults; 1% PrSM / 5% proteoform FDR [O: Yang 2020]"),
 22:dict(sep="CZE, LPA capillary, BGE 20% AA [O: Yang 2020]",cys="reduction/alkylation not reported [O: Yang 2020]",orig="TopPIC 1.3.1, max 1 mass shift, defaults; 1% PrSM / 5% proteoform FDR [O: Yang 2020]"),
 18:dict(sep="RPLC, C2 50 cm, 180 min; FAIMS CV -50..-20 + no-FAIMS [O: Fulcher 2021]",cys="TCEP reduction, no alkylation [O: Fulcher 2021]",orig="TopPIC 1.3; prec window 3 m/z; 15 ppm; 1 unknown mod <=500 Da; 1% proteoform FDR; CID 35% [O: Fulcher 2021]"),
 19:dict(sep="GELFrEE (8 fractions) + PLRP-S RPLC 90 min [O: Schaffer 2021]",cys="DTT reduction; alkylation not reported [O: Schaffer 2021]",orig="not TopPIC: Xtract + TDPortal (2.2 Da / 10 ppm, 1% FDR); CID 35% [O: Schaffer 2021]"),
 23:dict(sep="GELFrEE / IEX / nuclear-cytosolic / ProteoMiner + LC [O: Melani 2022 main text]",cys=NR+" in main text [O: Melani 2022]",orig="not TopPIC; 1% protein & proteoform FDR [O: Melani 2022]"),
 27:dict(sep="RPLC, C2 ~50 cm, 80 min [O: Zhou 2022]",cys=NR+" for TDP [O: Zhou 2022]",orig="TopPIC Suite 1.4.13; TopFD prec window 1 m/z, 0.02 m/z, MS1 S/N 3, MS2 S/N 1, max charge 30, max mass 50 kDa; TopPIC 15 ppm, cluster 3.2 Da, 1 shift +/-500 Da, FDR 0.01; HCD stepped 20/30/40 [O: Zhou 2022]"),
 32:dict(sep="RPLC, C4 60 cm, 100 min [O: Ramirez-Sagredo 2024]",cys="TCEP + ~20 mM iodoacetamide; Cys alkylation set as fixed mod [O: Ramirez-Sagredo 2024]",orig="TopPIC 1.4.10; max 2 mass shifts; 1% spectrum & proteoform FDR; HCD 35% [O: Ramirez-Sagredo 2024]"),
 6:dict(sep="RPLC, C2 50 cm, 160 min; FAIMS CV -50/-40/-30 [R: MassIVE MSV000093727 record]",cys="TCEP reduction, alkylation not mentioned [R: MassIVE record]",orig="TopPIC 1.5.4; prec window 3 m/z; 15 ppm; 1 unknown mod -150..4000 Da [R: MassIVE record]"),
 31:dict(sep="PEPPI gel fractionation (9 fractions) + PLRP-S RPLC 100 min [O: Takemori 2020]",cys="1 mM DTT + 2 mM iodoacetamide (carbamidomethyl Cys) [O: Takemori 2020]",orig="not TopPIC: TDPortal 2.2 Da / 10 ppm, fixed carbamidomethyl Cys, 1% FDR; CID 35% [O: Takemori 2020]"),
}
# separation stated in the publication title only (S1)
T={1:"CZE (per title)",12:"CZE (per title)",33:"CZE (per title)",15:"CE (per title; on-capillary lysis)",21:"PAGE fractionation + LC-FAIMS (per title)",26:"LC on C8 amine-bridged hybrid monolith (per title)",28:"LC on C8 amine-bridged hybrid monolith (per title)",25:"LC (per title)",3:"FAIMS (per title)",36:"FAIMS (per title)",17:"FAIMS with internal CV stepping (per title)"}
flags={28:"RESOLVED by human meta table: 24 CID + 16 ETD (exactly the 16 files named *ETD*); S5 collapses this subdataset to CID",19:"meta table agrees with S5 (CID for all 107); the 3 flagged file names contain both 'CID25' and 'HCD30', so the name alone is ambiguous - only scan headers would settle it",20:"",18:"MIXED Cys: 3 '1DLC_alkylated' files = Carbamidomethylation, other 124 = None (meta table)",1:"S5 sample 'E. coli K-12 25922' is self-contradictory (ATCC 25922 is not a K-12 strain) - check original paper",108:"EThcD: upstream TopRepo ships fix_ethcd_activation.py because msalign may label these ACTIVATION=ETD"}
cols=['subdataset','dataset_accession','project','publication_id','n_raw_files','species','sample','instrument','dissociation_S5','dissociation_meta','separation_meta','cysteine_protection_meta','toppic_fixed_mod','faims_meta','msalign_per_raw_S6','meta_source','publication','separation_original_paper','cysteine_treatment_original_paper','original_processing','project_id_rate','project_avg_proteoform_len','flag','sources']
w=csv.writer(open(sys.argv[2],'w',newline=''),delimiter='\t'); w.writerow(cols)
for r in sorted(S5,key=lambda r:(r[2],r[0])):
    sd,acc,p,n,sp,sam,ins,dis=r[:8]; s3=S3[p]; pub=S1[s3[1]]
    m=ms[sd]; _f=f"yes, multi-CV ({max(m)} msalign per raw file) [S6]" if max(m)>1 else "no multi-CV FAIMS within raw files [S6] (single-CV FAIMS runs are not detectable this way)"
    if p==18: _f="yes, one CV per raw file (CV -50..-20) + no-FAIMS runs [O: Fulcher 2021]"
    o=O.get(p,{})
    sep=o.get('sep', (T[p]+" [S1 title]; details: "+NOT) if p in T else NOT)
    idr=f"{s3[5]/s3[4]:.3f}"
    src="S1; S3; S5; S6" + ("; "+metasrc[sd] if sd in metasrc else "") + ("; original paper/record" if p in O else "")
    cm=mfmt(sd,'Cysteine_protection')
    fm={'None':'none (no -f)','Carbamidomethylation':'C57 (carbamidomethyl Cys)'}.get(cm, 'MIXED - set per raw file' if cm else 'unknown - meta table for this species not loaded')
    w.writerow([sd,acc,p,s3[1],n,cl(sp),cl(sam),cl(ins),cl(dis),mfmt(sd,'Dissociation') or 'not covered yet',mfmt(sd,'Separation') or 'not covered yet',cm or 'not covered yet',fm,mfmt(sd,'FAIMS') or 'not covered yet',f"max {max(m)}",metasrc.get(sd,'none yet'),
      f"{cl(pub[4])} {cl(pub[3])}. {cl(pub[5])} {pub[6]}. {cl(pub[2])}",
      sep,o.get('cys',"not in TopRepo supplement (S13 only says 'None or Carbamidomethylation'); "+NOT),
      o.get('orig',NOT),idr,f"{s3[8]:.1f}",flags.get(sd,''),src])
print(len(S5),'rows')
