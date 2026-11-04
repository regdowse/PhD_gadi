# Reference geometry for mom6-eddy-exp1

Copied metre-grid geometry and nonuniform vertical interfaces from
`mom6-idealised-eddy-348597bb/output001`. These files are geometry templates,
not a restart or an initial velocity/temperature state. The generator verifies
sizes, coordinates, spacing, bathymetry and ALE settings against exp1, then
recomputes Coriolis from exp1's current F_0, BETA and BETA_LAT_REF.
The centre-f geostrophic approximation is explicitly diagnosed for nonzero beta.
