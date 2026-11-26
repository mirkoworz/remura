"""V31.2 LAB — observed futures delta segments, not certified CVD.
Never join different provider/contract/provenance or bridge a missing window.
Input is synthetic or separately licensed. No network or order routing.
"""
def segments(windows,provenance):
    if provenance not in ("EXCHANGE_REPORTED","VENDOR_CLASSIFIED"):raise ValueError("provenance")
    if len(windows)>288:raise ValueError("capacity")
    result=[];last=None;total=0;segment=0
    for w in windows:
        identity=(w["provider"],w["instrument_id"],w["expiry"])
        start,end=w["start_ms"],w["end_ms"]
        if type(start) is not int or type(end) is not int or end-start!=300000:raise ValueError("window")
        if last and start<last[1]:raise ValueError("overlap")
        g=w["by_provenance"][provenance]
        buy,sell=g["buy"],g["sell"]
        if any(type(v) is not int or v<0 for v in (buy,sell,w["unknown_side_volume"])) or g["delta"]!=buy-sell:raise ValueError("delta")
        # Unknown side or mixed provenance means the selected series is partial.
        if not last or last!=(identity,start):
            total=0;segment+=1
        total+=g["delta"]
        result.append({"provider":identity[0],"instrument_id":identity[1],"expiry":identity[2],"end_ms":end,"segment":segment,"observed_delta":g["delta"],"observed_cumulative_delta":total,"side_provenance":provenance,"complete_coverage_verified":False,"cvd_certified":False,"prospective_admitted":False})
        last=(identity,end)
    return result
