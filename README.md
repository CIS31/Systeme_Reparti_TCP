# Systeme_Reparti_TCP

## Overview
This project aims to develop a **distributed system** where multiple machines in a lab environment collaborate to achieve a common goal while appearing as a single system to users. The machines communicate via **TCP sockets**, exchanging data and executing tasks efficiently.

The system consists of:
- A **master server** (handled by `Master.py`), responsible for coordinating tasks.
- **Multiple client machines** (handled by `Worker.py`), executing distributed computations.

---

## Main Functionalities and Execution Phases
The distributed application follows these key steps:

1. **Phase 1:** The master sends the names of the files to be processed to the client machines.
2. **Phase 2:** Clients establish TCP socket connections and distribute words from each file among themselves (**Shuffle1** process).
3. **Phase 3:** Client machines send grouped word frequency lists back to the master.
4. **Phase 4:** The master aggregates all received word lists, splits the data fairly, and redistributes them to client machines.
5. **Phase 5:** Clients exchange sub-lists among themselves for sorting based on frequency (**Shuffle2** process).
6. **Phase 6:** Clients sort the words by frequency and alphabetically, then send the final sorted results to the master.

### Performance Consideration - Amdahl’s Law
Amdahl’s Law helps evaluate potential performance improvements when using multiple processors or machines. It highlights that as more machines are added, the sequential portion of the program limits overall speedup.

---

## Prerequisites & Setup
Before running the system, ensure that network connections and deployment configurations are set correctly.

### Execution Steps
#### Configure `Deployement.sh`
Before launching the deployment script, modify `Deployement.sh` to include:
- The **username** for remote machine access.
- The **scripts** that should be executed on client machines.
- The **list of client machines**.

#### Run `Deployement.sh`
On any machine, unzip the project folder, open a terminal, and execute:
```bash
./Deployement.sh
```
This script will establish **TCP socket connections** with all client machines. Successful connections will output messages such as:
```bash
Socket bound to port {port} after {attempt + 1} attempts
```

#### Start `Master.py`
Once deployment is complete and all sockets are connected, choose a machine to run the master script:
```bash
python Master.py
```
This script initiates communication and task distribution.

#### End of Execution
- The process completes when the master **closes connections**.
- A `resultats.txt` file is generated, containing the final sorted data.

---

## Final Notes
- Ensure proper **network configuration** between machines before running the system.
- Use **real-time logging** to monitor the execution process.
- The system can be **scaled** by adding more machines, but performance gains may diminish due to overhead.

