## Restreaming Data from the ExciteOMeter App

The easiest way to restream the three streams, `RawECG`, `HeartRate`, and `RRinterval`, from the ExciteOMeter App that streams the LSL in the same WIFI network, is to use the script `stream_combined.py`.

If only a specific stream is desired, one can run `ecg_stream.py`, `hr_stream.py`, or `rr_stream.py`.

For personal use during development for a university project. Restreams the LSL signal to the same network which makes it detectable by the LSL Plugin in Unity. Includes processing of RR Stream for HRV markers.

## Requires the Excite-O-Meter App to be installed on a smartphone or computer with the ECG, HR and RR stream being active. Smartphone or computer has to be connected to the same network as machine running this script.
