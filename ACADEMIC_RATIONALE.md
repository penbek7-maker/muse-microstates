# Academic rationale and interpretation limits

## Purpose of the system

`muse_microstates.py` converts short-window EEG band-power variation into five operational states for musical interaction. The state labels support deterministic mapping in Max/MSP. They do not constitute a clinical or psychological classifier.

The term `microstates` in the filename refers to short operational interaction states. Conventional EEG microstate analysis instead examines brief, quasi-stable scalp-potential topographies using multichannel EEG. The present script does not perform that analysis.

## Exact signal model

The script analyses one Muse channel, AF7, in non-overlapping two-second windows sampled at 256 Hz. Welch's method estimates absolute power in four fixed bands:

- theta: 4–8 Hz
- alpha: 8–12 Hz
- beta: 13–30 Hz
- gamma: 30–45 Hz

Each band's current power is standardised against its own rolling history:

```text
z_band = (current_band_power - history_mean) / history_standard_deviation
```

The script treats a band as high when `z > 0.5`.

## State rules

The detector checks the rules in this order:

1. `theta_dominant`: theta exceeds the threshold and has a higher z-score than alpha, beta, and gamma.
2. `alpha_theta`: alpha and theta are high, while beta and gamma are not high.
3. `beta_gamma`: beta and gamma are high, while alpha and theta are not high.
4. `beta_alpha`: beta and alpha are high, while theta and gamma are not high.
5. `alpha_gamma`: alpha and gamma are high, while beta and theta are not high.
6. If no rule passes, the detector returns `neutral`.

These are Boolean decision rules. The script does not calculate pair scores, rank six possible pairs, or use a winner margin.

## Literature context

The literature discusses alpha and theta activity in internally oriented processing, memory, meditation, creative ideation, and some neurofeedback protocols for musical performance. These findings do not validate the script's exact Boolean rule as a universal measure of creativity or immersion.

Beta activity varies with sensorimotor processing and task context. Gamma-range scalp EEG can reflect neural activity, but it overlaps strongly with facial, jaw, scalp, and neck muscle activity. This is a central limitation during vocal improvisation.

Research on theta–gamma or alpha–gamma coupling typically examines phase relationships or phase-amplitude coupling. Simultaneously high band-power values do not measure coupling.

## Methodological boundaries

- The Muse 2 provides limited scalp coverage and does not support anatomical source localisation.
- The script analyses AF7 only.
- Fixed frequency bands do not account for individual differences in alpha peak frequency.
- The rolling z-score reduces scale differences but does not remove movement or muscle artefacts.
- The current window enters the rolling history before the z-score calculation.
- State priority affects the output. Because `theta_dominant` is checked first, it can take precedence over a pair state.
- A state transition should be interpreted as a computational event used by the artwork.

## Recommended presentation wording

> The system calculates baseline-relative band-power changes and applies five transparent rules to create operational musical interaction states. These states control processes in Max/MSP. They do not identify emotions or conventional EEG microstates.

## Selected references

- Benedek, M., et al. (2011). EEG alpha synchronization is related to top-down processing in convergent and divergent thinking. *Neuropsychologia*, 49(12), 3505–3511. https://doi.org/10.1016/j.neuropsychologia.2011.09.004
- Cavanagh, J. F., & Frank, M. J. (2014). Frontal theta as a mechanism for cognitive control. *Trends in Cognitive Sciences*, 18(8), 414–421. https://doi.org/10.1016/j.tics.2014.04.012
- Gruzelier, J. H., et al. (2014). Immediate effects of Alpha/theta and Sensory-Motor Rhythm feedback on music performance. *International Journal of Psychophysiology*, 93(1), 96–104. https://doi.org/10.1016/j.ijpsycho.2014.03.009
- Kilavik, B. E., et al. (2013). The ups and downs of beta oscillations in sensorimotor cortex. *Experimental Neurology*, 245, 15–26. https://doi.org/10.1016/j.expneurol.2012.09.014
- Michel, C. M., & Koenig, T. (2018). EEG microstates as a tool for studying the temporal dynamics of whole-brain neuronal networks. *NeuroImage*, 180, 577–593. https://doi.org/10.1016/j.neuroimage.2017.11.062
- Nottage, J. F., & Horder, J. (2016). State-of-the-art analysis of high-frequency gamma-range EEG in humans. *Neuropsychobiology*, 72(3–4), 219–228. https://doi.org/10.1159/000382023
