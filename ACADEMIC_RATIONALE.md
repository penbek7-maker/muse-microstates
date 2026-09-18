# Ακαδημαϊκή τεκμηρίωση και όρια της ανάλυσης ζευγών EEG

## Συμπέρασμα

Τα τέσσερα ζεύγη του `muse_microstates.py` δεν τεκμηριώνονται στη βιβλιογραφία ως τέσσερις διακριτές και αναγνωρισμένες «νοητικές μικροκαταστάσεις». Η βιβλιογραφία πράγματι μελετά σχέσεις μεταξύ ρυθμών, αλλά συνήθως ως:

- λόγους ισχύος (band-power ratios),
- μεταβολές ισχύος σε σχέση με πειραματική συνθήκη,
- συσχέτιση ή συγχρονισμό,
- phase–amplitude coupling (PAC),
- ή χωροχρονικά πρότυπα πολλών ηλεκτροδίων.

Ο αρχικός κανόνας ήταν διαφορετικός: χαρακτήριζε ένα ζεύγος όταν και τα δύο bands είχαν `z > 0.5` ως προς κυλιόμενη baseline και τα άλλα δύο όχι. Αυτός ο κανόνας δεν τεκμηριώνεται ως δημοσιευμένος νευροεπιστημονικός ταξινομητής ψυχικών καταστάσεων. Η αναθεωρημένη έκδοση συγκρίνει ισότιμα και τα έξι δυνατά ζεύγη.

## Αξιολόγηση των αρχικών ζευγών

| Ζεύγος | Τι στηρίζει η βιβλιογραφία | Τι δεν στηρίζει | Απόφαση |
|---|---|---|---|
| alpha–theta | Έχουν παρατηρηθεί αυξήσεις alpha και theta σε συγκεκριμένα πρωτόκολλα διαλογισμού. Το alpha/theta neurofeedback έχει επίσης μελετηθεί σε μουσική εκτέλεση και δημιουργικότητα. | Οι μελέτες δεν επικυρώνουν τον ακριβή κανόνα «alpha και theta υψηλά, beta και gamma όχι» ως γενική νοητική κατάσταση. Το neurofeedback συνήθως αφορά λόγο theta/alpha και ειδικό πρωτόκολλο. | Μερική, πλαισιοεξαρτώμενη στήριξη. |
| beta–gamma | Υπάρχουν φυσιολογικές αλληλεπιδράσεις beta–gamma και συνύπαρξη ρυθμών σε ειδικά πειραματικά/νευρωνικά πλαίσια. | Δεν προκύπτει γενική κατάσταση από ταυτόχρονα υψηλή ισχύ beta και gamma σε ένα μετωπιαίο κανάλι. | Δεν δικαιολογείται ως αυτόνομη νοητική κατάσταση. |
| alpha–beta | Alpha και beta συμμετέχουν σε δείκτες προσοχής/engagement. Κλασικό παράδειγμα είναι ο δείκτης `beta/(alpha+theta)`. | Αυτός ο δείκτης αντιπαραβάλλει beta με alpha/theta· δεν τεκμηριώνει ότι ταυτόχρονα υψηλά alpha και beta ορίζουν συγκεκριμένη κατάσταση. | Αδύναμη στήριξη για τον αρχικό κανόνα. |
| alpha–gamma | Υπάρχει ισχυρή βιβλιογραφία για alpha-phase/gamma-amplitude coupling σε συγκεκριμένες περιοχές και εργασίες. | PAC δεν σημαίνει ότι η ισχύς alpha και gamma είναι ταυτόχρονα υψηλή. Σε μελέτη οπτικού φλοιού, οι ισχείς τους ήταν μάλιστα αντιστρόφως συσχετισμένες. | Στηρίζεται η αλληλεπίδραση, όχι ο κανόνας co-high. |
| theta-dominant | Η theta σχετίζεται, ανάλογα με θέση και πειραματικό πλαίσιο, με υπνηλία, μνήμη, γνωστικό έλεγχο ή διαλογισμό. | Η κυριαρχία theta σε ένα μόνο κανάλι δεν αντιστοιχεί μονοσήμαντα σε μία νοητική κατάσταση. | Περιγραφικό χαρακτηριστικό, όχι έγκυρη ετικέτα κατάστασης. |

## Πώς λειτουργεί η αναθεωρημένη έκδοση

Το `muse_microstates.py` εξετάζει χωρίς προεπιλογή και τα έξι μη διατεταγμένα ζεύγη:

1. alpha–theta
2. beta–gamma
3. beta–alpha
4. alpha–gamma
5. theta–beta
6. theta–gamma

Για κάθε band μετατρέπει πρώτα την ισχύ σε dB και υπολογίζει z-score σε σχέση με το δικό του προηγούμενο rolling baseline. Για κάθε ζεύγος χρησιμοποιεί:

```text
pair_score(A, B) = (z_A + z_B) / 2
```

Όλα τα ζεύγη κατατάσσονται σε κάθε παράθυρο. Το πρώτο ζεύγος ενεργοποιείται μόνο όταν και τα δύο μέλη του έχουν `z > threshold` και το pair score του είναι μεγαλύτερο από όλα τα άλλα pair scores. Προαιρετικά, το `pair_margin` απαιτεί ελάχιστη διαφορά από το δεύτερο ζεύγος. Διαφορετικά η έξοδος είναι `neutral`.

Για παράδειγμα, το `alpha_theta_high` σημαίνει ότι ο μέσος όρος των `z_alpha` και `z_theta` είναι υψηλότερος από τους μέσους όρους των άλλων πέντε ζευγών και ότι τόσο το alpha όσο και το theta ξεπερνούν το threshold. Δεν απαιτεί πλέον τα beta και gamma να βρίσκονται κάτω από το threshold.

Το μέτρο είναι σκόπιμα περιγραφικό: δεν είναι δείκτης λειτουργικής συνδεσιμότητας, συγχρονισμού ή PAC και δεν αποδίδει ψυχολογική ετικέτα. Μαθηματικά, η νικήτρια δυάδα είναι ουσιαστικά τα δύο bands με τα υψηλότερα z-scores. Η ομαδοποίησή τους ως ζεύγος είναι χρήσιμη για το καλλιτεχνικό mapping, αλλά δεν αποδεικνύει ιδιαίτερη βιολογική αλληλεπίδραση μεταξύ τους.

Η πλήρης σύγκριση όλων των ζευγών μειώνει το πρόβλημα της αυθαίρετης επιλογής τεσσάρων από τα έξι, αλλά δεν μετατρέπει από μόνη της το αποτέλεσμα σε επικυρωμένο νευροεπιστημονικό μοντέλο.

## Σημαντικές μεθοδολογικές επιφυλάξεις

1. Ο όρος **EEG microstates** έχει ήδη ειδική επιστημονική σημασία: σύντομα, ημι-σταθερά πρότυπα της τοπογραφίας δυναμικού σε πολυκαναλικό EEG. Τα band-pair states του project δεν είναι EEG microstates με αυτή την καθιερωμένη έννοια. Για παρουσίαση προτείνονται οι όροι **rule-based spectral interaction states** ή **band-pair interaction states**.
2. Η ισχύς gamma σε scalp EEG είναι ιδιαίτερα ευάλωτη σε μυϊκό EMG, κινήσεις ματιών και μικροσυσπάσεις. Αυτό είναι κρίσιμο για Muse, ειδικά σε μετωπιαία/κροταφικά ηλεκτρόδια.
3. Οι σταθερές ζώνες συχνοτήτων είναι πρακτικές, αλλά η alpha peak frequency διαφέρει μεταξύ ατόμων. Για ισχυρότερη μελέτη χρειάζεται εξατομίκευση bands ή τουλάχιστον calibration ανά συμμετέχοντα.
4. Η συσχέτιση ενός EEG χαρακτηριστικού με συμπεριφορά απαιτεί πειραματικές συνθήκες, επαναλήψεις, ground truth και στατιστικό έλεγχο. Η ονομασία ενός realtime feature δεν αρκεί για αιτιώδη ή ψυχολογική ερμηνεία.
5. Τα αποτελέσματα επικύρωσης φορητών Muse συσκευών είναι πλαισιοεξαρτώμενα. Μελέτη του Muse 2 βρήκε χρησιμότητα σε συγκεκριμένο N-back workload protocol, αλλά μόνο 2 από 12 EEG measures διαφοροποίησαν σταθερά τα επίπεδα workload. Άλλη σύγκριση, σε Muse S Gen 2, βρήκε χαμηλή συμφωνία με research-grade EEG. Επομένως δεν πρέπει να γενικεύουμε από μία εργασία ή μία παραλλαγή της συσκευής.

## Προτεινόμενη διατύπωση για παρουσίαση

> Το σύστημα δεν επιχειρεί αναγνώριση συναισθημάτων ή κλινικών νοητικών καταστάσεων. Μετατρέπει αποκλίσεις της φασματικής ισχύος EEG από μια προσωπική κυλιόμενη baseline σε έξι περιγραφικά scores ζευγών και επιλέγει τη δυάδα με τη μεγαλύτερη κοινή αύξηση. Η χαρτογράφηση της νικήτριας δυάδας στον ήχο αποτελεί καλλιτεχνικό σχεδιασμό, ενημερωμένο από τη βιβλιογραφία των νευρωνικών ταλαντώσεων αλλά όχι ισοδύναμο με μέτρηση coupling ή γνωστική ταξινόμηση.

## Βιβλιογραφία

- Lagopoulos, J., et al. (2009). *Increased theta and alpha EEG activity during nondirective meditation*. Journal of Alternative and Complementary Medicine, 15(11), 1187–1192. https://doi.org/10.1089/acm.2009.0113
- Gruzelier, J. H. (2009). *A theory of alpha/theta neurofeedback, creative performance enhancement, long distance functional connectivity and psychological integration*. Cognitive Processing, 10(Suppl 1), S101–S109. https://doi.org/10.1007/s10339-008-0248-5
- Gruzelier, J. H., Hirst, L., Holmes, P., & Leach, J. (2014). *Immediate effects of Alpha/theta and Sensory-Motor Rhythm feedback on music performance*. International Journal of Psychophysiology, 93(1), 96–104. https://doi.org/10.1016/j.ijpsycho.2014.03.009
- Klimesch, W. (1999). *EEG alpha and theta oscillations reflect cognitive and memory performance: A review and analysis*. Brain Research Reviews, 29(2–3), 169–195. https://doi.org/10.1016/S0165-0173(98)00056-3
- Pope, A. T., Bogart, E. H., & Bartolome, D. S. (1995). *Biocybernetic system evaluates indices of operator engagement in automated task*. Biological Psychology, 40(1–2), 187–195. https://doi.org/10.1016/0301-0511(95)05116-3
- Roopun, A. K., et al. (2008). *Period concatenation underlies interactions between gamma and beta rhythms in neocortex*. Frontiers in Cellular Neuroscience, 2, 1. https://doi.org/10.3389/neuro.03.001.2008
- Voytek, B., et al. (2010). *Shifts in gamma phase-amplitude coupling frequency from theta to alpha over posterior cortex during visual tasks*. Frontiers in Human Neuroscience, 4, 191. https://doi.org/10.3389/fnhum.2010.00191
- Spaak, E., Bonnefond, M., Maier, A., Leopold, D. A., & Jensen, O. (2012). *Layer-specific entrainment of gamma-band neural activity by the alpha rhythm in monkey visual cortex*. Current Biology, 22(24), 2313–2318. https://doi.org/10.1016/j.cub.2012.10.020
- Michel, C. M., & Koenig, T. (2018). *EEG microstates as a tool for studying the temporal dynamics of whole-brain neuronal networks: A review*. NeuroImage, 180, 577–593. https://doi.org/10.1016/j.neuroimage.2017.11.062
- Whitham, E. M., et al. (2008). *Thinking activates EMG in scalp electrical recordings*. Clinical Neurophysiology, 119(5), 1166–1175. https://doi.org/10.1016/j.clinph.2008.01.024
- Zhang, L., & Cui, H. (2022). *Reliability of MUSE 2 and Tobii Pro Nano at capturing mobile application users' real-time cognitive workload changes*. Frontiers in Neuroscience, 16, 1011475. https://doi.org/10.3389/fnins.2022.1011475
- Mikhaylov, D., Saeed, M., Alhosani, M. H., & Al Wahedi, Y. F. (2024). *Comparison of EEG Signal Spectral Characteristics Obtained with Consumer- and Research-Grade Devices*. Sensors, 24(24), 8108. https://doi.org/10.3390/s24248108
