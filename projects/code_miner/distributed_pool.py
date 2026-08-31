from multiprocessing import Pool

def execute_tasks(tasks, workers=4):
    with Pool(workers) as p:
        return p.map(lambda f: f(), tasks)
