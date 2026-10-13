# Student protest tracker

A daily page of news reports of protest by students, country by country, built from the public files of the GDELT Project.
Each country is compared with its own past: the page shows where such reports are unusually numerous now.

**Page:** https://roddesbordes-dev.github.io/student-protest-tracker/ (English and French)

It is a screening tool: a flag is a reason to read the articles listed for the country, not a finding that students are
protesting there.

The page is refreshed every day at about 02:40 UTC by the workflow in `.github/workflows/update.yml`.

*Suivi quotidien des mentions, dans la presse, de protestations d'élèves et d'étudiants, pays par pays, à partir des fichiers
publics du projet GDELT. Une alerte est une raison de lire les articles listés pour le pays, non le constat que des étudiants
y protestent.*

Sources: the GDELT Project, events database and knowledge graph, version 2, https://www.gdeltproject.org; V-Dem Country-Year
Dataset v16, https://www.v-dem.net, for the press-freedom marker.

Author: Rodolphe Desbordes.
