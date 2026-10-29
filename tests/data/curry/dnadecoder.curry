-- http://science.sciencemag.org/content/355/6328/950.full

base_to_bin 'A' = "00"
base_to_bin 'C' = "01"
base_to_bin 'G' = "10"
base_to_bin 'T' = "11"

dna_to_binary seq = concatMap base_to_bin seq

-- inverse of dna_to_binary, there is not yet an "inverse" higher functio
-- binary_to_dna = inverse dna_to_binary

binary_to_dna (dna_to_binary seq) = seq

dna_sample = "GATTACA"
bin_sample = "10001111000100"

main = binary_to_dna bin_sample


-- @article {Erlich950,
-- 	author = {Erlich, Yaniv and Zielinski, Dina},
-- 	title = {DNA Fountain enables a robust and efficient storage architecture},
-- 	volume = {355},
-- 	number = {6328},
-- 	pages = {950--954},
-- 	year = {2017},
-- 	doi = {10.1126/science.aaj2038},
-- 	publisher = {American Association for the Advancement of Science},
-- 	abstract = {DNA has the potential to provide large-capacity information storage. However, current methods have only been able to use a fraction of the theoretical maximum. Erlich and Zielinski present a method, DNA Fountain, which approaches the theoretical maximum for information stored per nucleotide. They demonstrated efficient encoding of information{\textemdash}including a full computer operating system{\textemdash}into DNA that could be retrieved at scale after multiple rounds of polymerase chain reaction.Science, this issue p. 950DNA is an attractive medium to store digital information. Here we report a storage strategy, called DNA Fountain, that is highly robust and approaches the information capacity per nucleotide. Using our approach, we stored a full computer operating system, movie, and other files with a total of 2.14 {\texttimes} 106 bytes in DNA oligonucleotides and perfectly retrieved the information from a sequencing coverage equivalent to a single tile of Illumina sequencing. We also tested a process that can allow 2.18 {\texttimes} 1015 retrievals using the original DNA sample and were able to perfectly decode the data. Finally, we explored the limit of our architecture in terms of bytes per molecule and obtained a perfect retrieval from a density of 215 petabytes per gram of DNA, orders of magnitude higher than previous reports.},
-- 	issn = {0036-8075},
-- 	URL = {http://science.sciencemag.org/content/355/6328/950},
-- 	eprint = {http://science.sciencemag.org/content/355/6328/950.full.pdf},
-- 	journal = {Science}
-- }
-- 