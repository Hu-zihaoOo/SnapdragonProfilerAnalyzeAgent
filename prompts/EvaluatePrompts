GPU Primitive Processing:
Average Polygon Area – ideally at least 4, but not much larger than the bin dimensions

% Prims Clipped – Lower is better; ideally less than 2%

% Prims Trivially Rejected – Lower is better; ideally less than 2%

Reused Vertices – Higher is better; usually indicates indexed draws

GPU Shader Processing:
(Slow To Trace): % Linear Filtered – Lower is better; Linear Filtering tends to be expensive

(Slow To Trace): % Nearest Filtered – Higher is better; Nearest Filtering tends to be performant

% Shader ALU Capacity Utilized – Higher is better; ideally 50-100%

% Shaders Busy – Higher is better; ideally 50-100%

% Shaders Stalled – Lower is better; ideally less than 10%

% Texture Pipes Busy – Minimize within aesthetic constraints for battery consumption – even low values like 20%-30% can sometimes bottleneck the system, but values nearing 100% can sometimes not be a bottleneck

% Time ALUs Working – Higher is better; ideally 50%-100%

% Time Compute – Higher is better; when compute is active, ideally this metric might report near 100%. The percentage of the frame compute is active will vary dramatically based on the app

% Time EFUs Working – Higher is better; ideally at least 20%

% Time Shading Fragments – Higher is better; if you’re using a traditional vertex-and-fragment shading pipeline (instead of the compute-heavy GPU-driven approach), ideally this metric might report 100% for at least 60% of the frame

% Time Shading Vertices – Higher is better; if you’re using a traditional vertex-and-fragment shading pipeline (instead of the compute-heavy GPU-driven approach), ideally this metric might report 100% for less than 10%-20% of the frame

% Wave Context Occupancy – Higher is better; ideally at least 50% on average (likely with spikes)

ALU/Fragment – Higher is better (likely with spikes)

ALU/Vertex – Higher is better (likely with spikes)

Fragment ALU Instructions (Full) – Lower is better (ideally much lower than “Fragment ALU Instructions (Half)”)

Fragment ALU Instructions (Half) – Higher is better (ideally much higher than “Fragment ALU Instructions Full”)

Interpolation Instructions / Fragment – Lower is better (can be a source of stalls)

Textures/Fragment – Lower is better (particularly on a vertex shader)

GPU Stalls:
% Instruction Cache Miss – Lower is better; generally best to minimize, but in some cases even spikes as high as 80% may not bottleneck performance

% Stalled on System Memory – Lower is better; ideally usually less than 2%, perhaps with short spikes up to 30%

% Texture Fetch Stall – Lower is better; ideally usually less than 2%, perhaps with short spikes up to 20% (a sustained ~16% or higher is usually too high)

% Texture L1 Miss – Lower is better; ideally vacillating between 0% and under 50%, with occasional higher spikes

% Texture L2 Miss – Lower is better; ideally vacilliting between 0% and under 40%, with occasional higher spikes

% Vertex Fetch Stall – Lower is better; ideally usually 0%, with occasional spikes not exceeding 70%

Vulkan (for high-level visibility – binning passes are best kept to 10%-20% of renderpass; 30% is usually too much):
Concurrent binning

Per drawcall stages

Rendering stages

Rendering Workloads

GPU General
% CP Overhead – close to 0% at all times; should never exceed 20%

GPU % Bus Busy – Varies:
up to 25% average for a downclocked-GPU/battery-conscious app

up to 90% for a max-performance app

GPU % Utilization – Varies:
up to 40% average for a downclocked-GPU/battery-saver app

up to 90+% for a max-performance app

(Slow To Trace) GPU Memory Stats:
Avg Memory Latency Cycles – Lower is better; large spikes indicate slow shaders

Texture Memory Read BW – Lower is better; large spikes indicate slow shaders

Vertex Memory Read – If binning is slow, this can indicate why (high reads = low bandwidth; low reads = stalls)

Write Total – Lower is better; writes to main memory tend to be expensive