Powershell utskrift pidfeilsøking: 
(venv) PS C:\Users\trulstam\OneDrive - Universitetet i Oslo\Documents\GitHub\Musehypothermi> python gui_core_v3.py
🚀 Starting Musehypothermi GUI v3.0 with Asymmetric PID...
✅ QApplication created
🚀 Initializing GUI v3.0...
✅ Data structures initialized
✅ Matplotlib plots configured
✅ MatplotlibGraphWidget initialized
✅ Graph widget created
✅ UI initialized
✅ SerialManager initialized
✅ CSV event log initialized: logs\gui_v3_events_20251105_133323.csv
✅ JSON event log initialized: logs\gui_v3_events_20251105_133323.json
✅ EventLogger initialized
✅ ProfileLoader initialized
LOG: 🔄 Found 2 ports
✅ All managers initialized
✅ GUI v3.0 initialized!
✅ Application started successfully
✅ Connected to COM4 at 115200 baud.
LOG: 🔌 Connected to COM4
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⚡ Logged event: Connected to COM4 at 2025-11-05 13:33:27
⬇️ Received: {"event":"✅ Failsafe cleared after heartbeat recovery"}
LOG: 📢 EVENT: ✅ Failsafe cleared after heartbeat recovery
⚡ Logged event: ✅ Failsafe cleared after heartbeat recovery at 2025-11-05 13:33:27
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
LOG: 🔄 Syncing...
➡️ Sent: {"CMD": {"action": "get", "state": "pid_params"}}
⬇️ Received: {"pid_kp":1,"pid_ki":0.1,"pid_kd":1,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_mode":"cooling"}
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.33637717,"anal_probe_temp":21.44055953,"pid_output":0,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.266595,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
📊 Graph update #1: 1 points
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.30973366,"anal_probe_temp":21.42986394,"pid_output":0,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.266595,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.26710196,"anal_probe_temp":21.38708509,"pid_output":0,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.266595,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.25644363,"anal_probe_temp":21.37639124,"pid_output":0,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.266595,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"SET": {"variable": "target_temp", "value": 20.0}}
⚡ Logged event: SET: target_temp → 20.00°C at 2025-11-05 13:33:35
LOG: ✅ Target set: 20.00°C
⬇️ Received: {"response":"Target temperature updated"}
LOG: 📥 RESPONSE: Target temperature updated
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.24045582,"anal_probe_temp":21.3336193,"pid_output":0,"breath_freq_bpm":23.78357,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.266595,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.20847907,"anal_probe_temp":21.37104445,"pid_output":0,"breath_freq_bpm":23.78357,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.266595,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "pid", "state": "start"}}
⚡ Logged event: CMD: pid → start at 2025-11-05 13:33:41
LOG: 📡 Sent: pid = start
⬇️ Received: {"event":"🚀 Asymmetric PID started"}
LOG: 📢 EVENT: 🚀 Asymmetric PID started
⚡ Logged event: 🚀 Asymmetric PID started at 2025-11-05 13:33:41
⬇️ Received: {"response":"PID started"}
LOG: 📥 RESPONSE: PID started
⬇️ Received: {"event":"🔥 Switched to heating mode"}
LOG: 📢 EVENT: 🔥 Switched to heating mode
⚡ Logged event: 🔥 Switched to heating mode at 2025-11-05 13:33:41
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.22446764,"anal_probe_temp":21.37104445,"pid_output":3.461136,"breath_freq_bpm":23.78357,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.27243107,"anal_probe_temp":21.37639124,"pid_output":4.195079,"breath_freq_bpm":11.98322,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.053291,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.53883766,"anal_probe_temp":21.38173812,"pid_output":4.603314,"breath_freq_bpm":11.98322,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.106546,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.09272791,"anal_probe_temp":21.40312651,"pid_output":4.703066,"breath_freq_bpm":11.98322,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.106496,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.90201989,"anal_probe_temp":21.40847382,"pid_output":4.221482,"breath_freq_bpm":11.98322,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.212976,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
📊 Graph update #11: 11 points
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":19.87673023,"anal_probe_temp":21.41382122,"pid_output":3.194498,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.532886,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
⬇️ Received: {"event":"❄️ Switched to cooling mode"}
LOG: 📢 EVENT: ❄️ Switched to cooling mode
⚡ Logged event: ❄️ Switched to cooling mode at 2025-11-05 13:34:01
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":20.93288527,"anal_probe_temp":21.45660358,"pid_output":-1.286857,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.267003,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.02403803,"anal_probe_temp":21.53148642,"pid_output":-2.848438,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.26791,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.88286322,"anal_probe_temp":21.5635845,"pid_output":-4.37123,"breath_freq_bpm":5.997002,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.215091,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":23.2973399,"anal_probe_temp":21.59568589,"pid_output":-5.569514,"breath_freq_bpm":5.997002,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.053882,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":23.28117582,"anal_probe_temp":21.59568589,"pid_output":-6.450083,"breath_freq_bpm":5.997002,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.053879,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.92588787,"anal_probe_temp":21.60103644,"pid_output":-6.898845,"breath_freq_bpm":5.997002,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.215155,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.36183895,"anal_probe_temp":21.58498505,"pid_output":-7.099698,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.214628,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":21.65989874,"anal_probe_temp":21.60638709,"pid_output":-6.925657,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.321115,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":20.90084512,"anal_probe_temp":21.5635845,"pid_output":-6.564554,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.266999,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
📊 Graph update #21: 21 points
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":20.10591916,"anal_probe_temp":21.51543861,"pid_output":-5.97848,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.213242,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
⬇️ Received: {"event":"🔥 Switched to heating mode"}
LOG: 📢 EVENT: 🔥 Switched to heating mode
⚡ Logged event: 🔥 Switched to heating mode at 2025-11-05 13:34:31
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":19.30671823,"anal_probe_temp":21.55288477,"pid_output":1.012249,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":-0.266287,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.57191833,"anal_probe_temp":21.57963478,"pid_output":1.743829,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.159723,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.98622895,"anal_probe_temp":21.54753505,"pid_output":2.99088,"breath_freq_bpm":12,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":-0.053251,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.87439713,"anal_probe_temp":21.49939162,"pid_output":3.57979,"breath_freq_bpm":12,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.106511,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.22584334,"anal_probe_temp":21.47264842,"pid_output":3.739803,"breath_freq_bpm":12,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.159734,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.91799323,"anal_probe_temp":21.50474052,"pid_output":3.391921,"breath_freq_bpm":12,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.266222,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":19.85008544,"anal_probe_temp":21.48869407,"pid_output":2.668897,"breath_freq_bpm":11.9988,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.213151,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
⬇️ Received: {"event":"❄️ Switched to cooling mode"}
LOG: 📢 EVENT: ❄️ Switched to cooling mode
⚡ Logged event: ❄️ Switched to cooling mode at 2025-11-05 13:34:52
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":20.92754507,"anal_probe_temp":21.52078779,"pid_output":-1.411154,"breath_freq_bpm":11.9988,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.427191,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.01867962,"anal_probe_temp":21.59568589,"pid_output":-2.786023,"breath_freq_bpm":11.9988,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.160746,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
📊 Graph update #31: 31 points
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.9151309,"anal_probe_temp":21.61708867,"pid_output":-4.412621,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.215123,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":23.36200932,"anal_probe_temp":21.63849295,"pid_output":-5.723006,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.161693,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":23.37278961,"anal_probe_temp":21.6224396,"pid_output":-6.572519,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.053904,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":1,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "set_cooling_pid", "params": {"kp": 0.5, "ki": 0.1, "kd": 1.0}}}
⚡ Logged event: ASYMMETRIC_CMD: set_cooling_pid → {'kp': 0.5, 'ki': 0.1, 'kd': 1.0} at 2025-11-05 13:35:07
LOG: ❄️ Cooling PID set: Kp=0.500, Ki=0.1000, Kd=1.000
⬇️ Received: {"event":"🧊 Cooling PID parameters committed (kp=0.5000, ki=0.1000, kd=1.0000)"}
LOG: 📢 EVENT: 🧊 Cooling PID parameters committed (kp=0.5000, ki=0.1000, kd=1.0000)
⚡ Logged event: 🧊 Cooling PID parameters committed (kp=0.5000, ki=0.1000, kd=1.0000) at 2025-11-05 13:35:07
⬇️ Received: {"event":"🧊 Cooling PID via GUI (kp=0.5000, ki=0.1000, kd=1.0000)"}
LOG: 📢 EVENT: 🧊 Cooling PID via GUI (kp=0.5000, ki=0.1000, kd=1.0000)
⚡ Logged event: 🧊 Cooling PID via GUI (kp=0.5000, ki=0.1000, kd=1.0000) at 2025-11-05 13:35:07
⬇️ Received: {"response":"Cooling PID updated"}
LOG: 📥 RESPONSE: Cooling PID updated
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":23.06039548,"anal_probe_temp":21.57963478,"pid_output":-5.507504,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.215292,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.51748745,"anal_probe_temp":21.52613706,"pid_output":-6.08228,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.107381,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "set_heating_pid", "params": {"kp": 1.0, "ki": 0.1, "kd": 1.0}}}
⚡ Logged event: ASYMMETRIC_CMD: set_heating_pid → {'kp': 1.0, 'ki': 0.1, 'kd': 1.0} at 2025-11-05 13:35:11
LOG: Heating PID set: Kp=1.000, Ki=0.1000, Kd=1.000
⬇️ Received: {"event":"🔥 Heating PID parameters committed (kp=1.0000, ki=0.1000, kd=1.0000)"}
LOG: 📢 EVENT: 🔥 Heating PID parameters committed (kp=1.0000, ki=0.1000, kd=1.0000)
⚡ Logged event: 🔥 Heating PID parameters committed (kp=1.0000, ki=0.1000, kd=1.0000) at 2025-11-05 13:35:11
⬇️ Received: {"event":"🔥 Heating PID via GUI (kp=1.0000, ki=0.1000, kd=1.0000)"}
LOG: 📢 EVENT: 🔥 Heating PID via GUI (kp=1.0000, ki=0.1000, kd=1.0000)
⚡ Logged event: 🔥 Heating PID via GUI (kp=1.0000, ki=0.1000, kd=1.0000) at 2025-11-05 13:35:11
⬇️ Received: {"response":"Heating PID updated"}
LOG: 📥 RESPONSE: Heating PID updated
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":21.84726531,"anal_probe_temp":21.57963478,"pid_output":-6.326053,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.21421,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":21.08244114,"anal_probe_temp":21.5689345,"pid_output":-6.293358,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.320554,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":1,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "set_heating_pid", "params": {"kp": 0.5, "ki": 0.1, "kd": 1.0}}}
⚡ Logged event: ASYMMETRIC_CMD: set_heating_pid → {'kp': 0.5, 'ki': 0.1, 'kd': 1.0} at 2025-11-05 13:35:17
LOG: Heating PID set: Kp=0.500, Ki=0.1000, Kd=1.000
⬇️ Received: {"event":"🔥 Heating PID parameters committed (kp=0.5000, ki=0.1000, kd=1.0000)"}
LOG: 📢 EVENT: 🔥 Heating PID parameters committed (kp=0.5000, ki=0.1000, kd=1.0000)
⚡ Logged event: 🔥 Heating PID parameters committed (kp=0.5000, ki=0.1000, kd=1.0000) at 2025-11-05 13:35:17
⬇️ Received: {"event":"🔥 Heating PID via GUI (kp=0.5000, ki=0.1000, kd=1.0000)"}
LOG: 📢 EVENT: 🔥 Heating PID via GUI (kp=0.5000, ki=0.1000, kd=1.0000)
⚡ Logged event: 🔥 Heating PID via GUI (kp=0.5000, ki=0.1000, kd=1.0000) at 2025-11-05 13:35:17
⬇️ Received: {"response":"Heating PID updated"}
LOG: 📥 RESPONSE: Heating PID updated
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":20.29786503,"anal_probe_temp":21.52613706,"pid_output":-6.222569,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.159985,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"event":"🔥 Switched to heating mode"}
LOG: 📢 EVENT: 🔥 Switched to heating mode
⚡ Logged event: 🔥 Switched to heating mode at 2025-11-05 13:35:23
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":19.49845889,"anal_probe_temp":21.48869407,"pid_output":0.204629,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":-0.266334,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.73164246,"anal_probe_temp":21.44055953,"pid_output":1.060106,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":-0.106484,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
📊 Graph update #41: 41 points
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.09805269,"anal_probe_temp":21.38173812,"pid_output":1.865712,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":-0.159743,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.88504817,"anal_probe_temp":21.37104445,"pid_output":2.474576,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.1512997,"anal_probe_temp":21.40847382,"pid_output":2.746463,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.15974,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.78488461,"anal_probe_temp":21.4940428,"pid_output":2.791191,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.266211,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":19.67958127,"anal_probe_temp":21.53148642,"pid_output":2.486637,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.319655,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
⬇️ Received: {"event":"❄️ Switched to cooling mode"}
LOG: 📢 EVENT: ❄️ Switched to cooling mode
⚡ Logged event: ❄️ Switched to cooling mode at 2025-11-05 13:35:43
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":20.71933197,"anal_probe_temp":21.52613706,"pid_output":-0.762799,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.373607,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":21.8365554,"anal_probe_temp":21.59033542,"pid_output":-1.735296,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.428357,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.79146388,"anal_probe_temp":21.64384425,"pid_output":-2.823092,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.322496,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":23.31889403,"anal_probe_temp":21.72412525,"pid_output":-3.867138,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.161658,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":23.40513404,"anal_probe_temp":21.76159715,"pid_output":-4.65045,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.107827,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
📊 Graph update #51: 51 points
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":23.13575724,"anal_probe_temp":21.79907384,"pid_output":-5.589792,"breath_freq_bpm":12,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.63026184,"anal_probe_temp":21.78836572,"pid_output":-6.089781,"breath_freq_bpm":12,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.161151,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "set_cooling_pid", "params": {"kp": 0.5, "ki": 0.1, "kd": 0.1}}}
⚡ Logged event: ASYMMETRIC_CMD: set_cooling_pid → {'kp': 0.5, 'ki': 0.1, 'kd': 0.1} at 2025-11-05 13:36:04
LOG: ❄️ Cooling PID set: Kp=0.500, Ki=0.1000, Kd=0.100
⬇️ Received: {"event":"🧊 Cooling PID parameters committed (kp=0.5000, ki=0.1000, kd=0.1000)"}
LOG: 📢 EVENT: 🧊 Cooling PID parameters committed (kp=0.5000, ki=0.1000, kd=0.1000)
⚡ Logged event: 🧊 Cooling PID parameters committed (kp=0.5000, ki=0.1000, kd=0.1000) at 2025-11-05 13:36:04
⬇️ Received: {"event":"🧊 Cooling PID via GUI (kp=0.5000, ki=0.1000, kd=0.1000)"}
LOG: 📢 EVENT: 🧊 Cooling PID via GUI (kp=0.5000, ki=0.1000, kd=0.1000)
⚡ Logged event: 🧊 Cooling PID via GUI (kp=0.5000, ki=0.1000, kd=0.1000) at 2025-11-05 13:36:04
⬇️ Received: {"response":"Cooling PID updated"}
LOG: 📥 RESPONSE: Cooling PID updated
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":21.96510125,"anal_probe_temp":21.7508904,"pid_output":-6.583463,"breath_freq_bpm":12,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.214301,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":21.23205756,"anal_probe_temp":21.69736253,"pid_output":-6.693478,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.267239,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "set_heating_pid", "params": {"kp": 0.5, "ki": 0.1, "kd": 1.0}}}
⚡ Logged event: ASYMMETRIC_CMD: set_heating_pid → {'kp': 0.5, 'ki': 0.1, 'kd': 1.0} at 2025-11-05 13:36:08
LOG: Heating PID set: Kp=0.500, Ki=0.1000, Kd=1.000
⬇️ Received: {"event":"🔥 Heating PID parameters committed (kp=0.5000, ki=0.1000, kd=1.0000)"}
LOG: 📢 EVENT: 🔥 Heating PID parameters committed (kp=0.5000, ki=0.1000, kd=1.0000)
⚡ Logged event: 🔥 Heating PID parameters committed (kp=0.5000, ki=0.1000, kd=1.0000) at 2025-11-05 13:36:08
⬇️ Received: {"event":"🔥 Heating PID via GUI (kp=0.5000, ki=0.1000, kd=1.0000)"}
LOG: 📢 EVENT: 🔥 Heating PID via GUI (kp=0.5000, ki=0.1000, kd=1.0000)
⚡ Logged event: 🔥 Heating PID via GUI (kp=0.5000, ki=0.1000, kd=1.0000) at 2025-11-05 13:36:08
⬇️ Received: {"response":"Heating PID updated"}
LOG: 📥 RESPONSE: Heating PID updated
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":20.46320674,"anal_probe_temp":21.63849295,"pid_output":-6.543429,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.426777,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":19.66359839,"anal_probe_temp":21.57428459,"pid_output":-6.164933,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.266383,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
⬇️ Received: {"event":"🔥 Switched to heating mode"}
LOG: 📢 EVENT: 🔥 Switched to heating mode
⚡ Logged event: 🔥 Switched to heating mode at 2025-11-05 13:36:14
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.87539787,"anal_probe_temp":21.55288477,"pid_output":0.978592,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":-0.212976,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.19389635,"anal_probe_temp":21.54218541,"pid_output":1.712017,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":-0.159735,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.89037366,"anal_probe_temp":21.57963478,"pid_output":2.407774,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":-0.159763,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.06610379,"anal_probe_temp":21.60638709,"pid_output":2.716954,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.106498,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
📊 Graph update #61: 61 points
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.63580773,"anal_probe_temp":21.65454715,"pid_output":2.824834,"breath_freq_bpm":23.9904,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.212965,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":19.48780573,"anal_probe_temp":21.65989874,"pid_output":2.587668,"breath_freq_bpm":23.9904,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.319588,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"event":"❄️ Switched to cooling mode"}
LOG: 📢 EVENT: ❄️ Switched to cooling mode
⚡ Logged event: ❄️ Switched to cooling mode at 2025-11-05 13:36:35
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":20.50588446,"anal_probe_temp":21.72947809,"pid_output":-0.206401,"breath_freq_bpm":23.9904,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.320086,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":21.61708867,"anal_probe_temp":21.78301181,"pid_output":-1.167407,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.535042,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.61414788,"anal_probe_temp":21.76695066,"pid_output":-2.290478,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.268541,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":23.2434647,"anal_probe_temp":21.78836572,"pid_output":-3.488815,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.21546,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":23.39974293,"anal_probe_temp":21.75624373,"pid_output":-4.550792,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.107824,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":23.19498931,"anal_probe_temp":21.64919565,"pid_output":-5.437732,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.161572,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.73771712,"anal_probe_temp":21.59568589,"pid_output":-6.113853,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.053741,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.09906708,"anal_probe_temp":21.63314174,"pid_output":-6.509703,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.214408,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
📊 Graph update #71: 71 points
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":21.38173812,"anal_probe_temp":21.63849295,"pid_output":-6.675555,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.160412,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":20.60192341,"anal_probe_temp":21.6224396,"pid_output":-6.574383,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.26681,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "set_cooling_pid", "params": {"kp": 0.5, "ki": 0.1, "kd": 0.1}}}
⚡ Logged event: ASYMMETRIC_CMD: set_cooling_pid → {'kp': 0.5, 'ki': 0.1, 'kd': 0.1} at 2025-11-05 13:37:03
LOG: ❄️ Cooling PID set: Kp=0.500, Ki=0.1000, Kd=0.100
⬇️ Received: {"event":"🧊 Cooling PID parameters committed (kp=0.5000, ki=0.1000, kd=0.1000)"}
LOG: 📢 EVENT: 🧊 Cooling PID parameters committed (kp=0.5000, ki=0.1000, kd=0.1000)
⚡ Logged event: 🧊 Cooling PID parameters committed (kp=0.5000, ki=0.1000, kd=0.1000) at 2025-11-05 13:37:03
⬇️ Received: {"event":"🧊 Cooling PID via GUI (kp=0.5000, ki=0.1000, kd=0.1000)"}
LOG: 📢 EVENT: 🧊 Cooling PID via GUI (kp=0.5000, ki=0.1000, kd=0.1000)
⚡ Logged event: 🧊 Cooling PID via GUI (kp=0.5000, ki=0.1000, kd=0.1000) at 2025-11-05 13:37:04
⬇️ Received: {"response":"Cooling PID updated"}
LOG: 📥 RESPONSE: Cooling PID updated
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":19.82344163,"anal_probe_temp":21.59033542,"pid_output":-6.249915,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.21315,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":0.5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
⬇️ Received: {"event":"🔥 Switched to heating mode"}
LOG: 📢 EVENT: 🔥 Switched to heating mode
⚡ Logged event: 🔥 Switched to heating mode at 2025-11-05 13:37:06
➡️ Sent: {"CMD": {"action": "set_cooling_pid", "params": {"kp": 5.0, "ki": 0.1, "kd": 0.1}}}
⚡ Logged event: ASYMMETRIC_CMD: set_cooling_pid → {'kp': 5.0, 'ki': 0.1, 'kd': 0.1} at 2025-11-05 13:37:07
LOG: ❄️ Cooling PID set: Kp=5.000, Ki=0.1000, Kd=0.100
⬇️ Received: {"event":"🧊 Cooling PID parameters committed (kp=5.0000, ki=0.1000, kd=0.1000)"}
LOG: 📢 EVENT: 🧊 Cooling PID parameters committed (kp=5.0000, ki=0.1000, kd=0.1000)
⚡ Logged event: 🧊 Cooling PID parameters committed (kp=5.0000, ki=0.1000, kd=0.1000) at 2025-11-05 13:37:07
⬇️ Received: {"event":"🧊 Cooling PID via GUI (kp=5.0000, ki=0.1000, kd=0.1000)"}
LOG: 📢 EVENT: 🧊 Cooling PID via GUI (kp=5.0000, ki=0.1000, kd=0.1000)
⚡ Logged event: 🧊 Cooling PID via GUI (kp=5.0000, ki=0.1000, kd=0.1000) at 2025-11-05 13:37:07
⬇️ Received: {"response":"Cooling PID updated"}
LOG: 📥 RESPONSE: Cooling PID updated
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":19.04045903,"anal_probe_temp":21.59568589,"pid_output":0.867282,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":-0.266239,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":0.5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "set_heating_pid", "params": {"kp": 5.0, "ki": 0.1, "kd": 1.0}}}
⚡ Logged event: ASYMMETRIC_CMD: set_heating_pid → {'kp': 5.0, 'ki': 0.1, 'kd': 1.0} at 2025-11-05 13:37:10
LOG: Heating PID set: Kp=5.000, Ki=0.1000, Kd=1.000
⬇️ Received: {"event":"🔥 Heating PID parameters committed (kp=5.0000, ki=0.1000, kd=1.0000)"}
LOG: 📢 EVENT: 🔥 Heating PID parameters committed (kp=5.0000, ki=0.1000, kd=1.0000)
⚡ Logged event: 🔥 Heating PID parameters committed (kp=5.0000, ki=0.1000, kd=1.0000) at 2025-11-05 13:37:10
⬇️ Received: {"event":"🔥 Heating PID via GUI (kp=5.0000, ki=0.1000, kd=1.0000)"}
LOG: 📢 EVENT: 🔥 Heating PID via GUI (kp=5.0000, ki=0.1000, kd=1.0000)
⚡ Logged event: 🔥 Heating PID via GUI (kp=5.0000, ki=0.1000, kd=1.0000) at 2025-11-05 13:37:10
⬇️ Received: {"response":"Heating PID updated"}
LOG: 📥 RESPONSE: Heating PID updated
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.31635782,"anal_probe_temp":21.59033542,"pid_output":9.134624,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":-0.212972,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.91700078,"anal_probe_temp":21.60103644,"pid_output":11.54548,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.98090382,"anal_probe_temp":21.61173783,"pid_output":11.71783,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.159755,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.48140826,"anal_probe_temp":21.61173783,"pid_output":9.6714,"breath_freq_bpm":5.98444,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.212966,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":19.27476453,"anal_probe_temp":21.59568589,"pid_output":5.930381,"breath_freq_bpm":5.98444,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.372783,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":20.26586947,"anal_probe_temp":21.65454715,"pid_output":0.975149,"breath_freq_bpm":5.98444,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.479898,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
📊 Graph update #81: 81 points
⬇️ Received: {"event":"❄️ Switched to cooling mode"}
LOG: 📢 EVENT: ❄️ Switched to cooling mode
⚡ Logged event: ❄️ Switched to cooling mode at 2025-11-05 13:37:26
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":21.35500459,"anal_probe_temp":21.69201027,"pid_output":-6.980748,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.374234,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.42086629,"anal_probe_temp":21.65989874,"pid_output":-12.8829,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.375645,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":23.15190975,"anal_probe_temp":21.64384425,"pid_output":-17.39106,"breath_freq_bpm":6,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.107685,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":23.42669996,"anal_probe_temp":21.61173783,"pid_output":-19.76438,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0.053917,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
LOG: 📥 RESPONSE: heartbeat_ack
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":23.2973399,"anal_probe_temp":21.60638709,"pid_output":-20.13436,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":0,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.87210838,"anal_probe_temp":21.5635845,"pid_output":-18.94176,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.161325,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":22.27600609,"anal_probe_temp":21.55288477,"pid_output":-16.73417,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.107275,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":21.5635845,"anal_probe_temp":21.5689345,"pid_output":-13.74737,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.160503,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":20.78872468,"anal_probe_temp":21.54753505,"pid_output":-10.2252,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.213539,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":20.00463961,"anal_probe_temp":21.54218541,"pid_output":-6.420816,"breath_freq_bpm":0,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":true,"emergency_stop":false,"temperature_rate":-0.213206,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
📊 Graph update #91: 91 points
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
⬇️ Received: {"event":"🔥 Switched to heating mode"}
LOG: 📢 EVENT: 🔥 Switched to heating mode
⚡ Logged event: 🔥 Switched to heating mode at 2025-11-05 13:37:58
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":19.20553415,"anal_probe_temp":21.54753505,"pid_output":4.271765,"breath_freq_bpm":12,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":-0.266267,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.45478754,"anal_probe_temp":21.50474052,"pid_output":8.367662,"breath_freq_bpm":12,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":-0.266207,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.94895265,"anal_probe_temp":21.45660358,"pid_output":11.25223,"breath_freq_bpm":12,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
➡️ Sent: {"CMD": {"action": "pid", "state": "stop"}}
⚡ Logged event: CMD: pid → stop at 2025-11-05 13:38:08
LOG: 📡 Sent: pid = stop
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":17.90102457,"anal_probe_temp":21.4352117,"pid_output":12.03147,"breath_freq_bpm":5.9994,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.053254,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
⬇️ Received: {"event":"⏹️ Asymmetric PID stopped"}
⬇️ Received: {"response":"PID stopped"}
LOG: 📢 EVENT: ⏹️ Asymmetric PID stopped
⚡ Logged event: ⏹️ Asymmetric PID stopped at 2025-11-05 13:38:08
LOG: 📥 RESPONSE: PID stopped
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.30570919,"anal_probe_temp":21.38708509,"pid_output":0,"breath_freq_bpm":5.9994,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.053254,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
➡️ Sent: {"CMD": {"action": "heartbeat", "state": "ping"}}
⬇️ Received: {"response":"heartbeat_ack"}
LOG: 📥 RESPONSE: heartbeat_ack
➡️ Sent: {"CMD": {"action": "get", "state": "status"}}
⬇️ Received: {"failsafe_active":false,"failsafe_reason":"","cooling_plate_temp":18.9233177,"anal_probe_temp":21.38173812,"pid_output":0,"breath_freq_bpm":5.9994,"breathing_failsafe_enabled":true,"debug_level":0,"plate_target_active":20,"profile_active":false,"profile_paused":false,"profile_step":0,"profile_remaining_time":0,"autotune_active":false,"autotune_status":"idle","cooling_mode":false,"emergency_stop":false,"temperature_rate":0.053254,"asymmetric_autotune_active":false,"pid_max_output":100,"pid_heating_limit":100,"pid_cooling_limit":100,"pid_heating_kp":5,"pid_heating_ki":0.1,"pid_heating_kd":1,"pid_cooling_kp":5,"pid_cooling_ki":0.1,"pid_cooling_kd":0.1,"cooling_rate_limit":2,"deadband":0.5,"safety_margin":2}
🛑 Disconnecting SerialManager...
✅ Disconnected.
LOG: 🔌 Disconnected
⚡ Logged event: Disconnected at 2025-11-05 13:38:15
LOG: 👋 Application closing...
📝 Closing event logger and flushing JSON...
✅ Event logger closed.
LOG: ✅ Cleanup complete
(venv) PS C:\Users\trulstam\OneDrive - Universitetet i Oslo\Documents\GitHub\Musehypothermi>
