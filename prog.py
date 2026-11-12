import yaml
import urllib.request
import json
from graphviz import Digraph

# ==========================================
# ЭТАП 1: Загрузка конфигурации и вывод параметров
# ==========================================
def load_config():
    with open("conf.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    
    print("--- Параметры (ключ-значение) ---")
    for key, value in cfg.items():
        print(f"{key}: {value}")
    
    # Обработка ошибок (проверка, что имя пакета есть)
    if not cfg.get("package_name"):
        raise ValueError("Ошибка: Не указано имя пакета в config.yaml")
    return cfg

# ==========================================
# ЭТАП 2: Сбор данных (PyPI без pip)
# ==========================================
def get_dependencies(pkg_name, repo_url):
    url = f"{repo_url}/{pkg_name}/json"
    try:
        # Скачиваем JSON с сайта
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
        
        # Достаем список зависимостей
        requires = data['info'].get('requires_dist')
        if not requires:
            return []
        
        deps = []
        for req in requires:
            # Очищаем строку от версий (например "urllib3<3,>=1" -> "urllib3")
            dep_name = req.split(' ')[0].split(';')[0].split('[')[0].strip().lower()
            deps.append(dep_name)
        return deps
    except Exception:
        return [] # Если пакет не найден или ошибка сети

# ==========================================
# ЭТАП 3: Построение графа (DFS без рекурсии)
# ==========================================
def build_graph(root_pkg, cfg):
    graph = {}
    visited = set()
    
    # Стек для DFS: кладем кортеж (имя пакета, текущая глубина)
    stack = [(root_pkg, 0)]
    
    while stack:
        pkg, depth = stack.pop() # Берем последний из стека
        
        # Если уже смотрели, или достигли дна — пропускаем
        if pkg in visited or depth >= cfg['max_depth']:
            continue
        
        visited.add(pkg)
        
        # Режим тестирования (Этап 3)
        if cfg.get('test_mode') and cfg.get('test_file'):
            deps = get_test_dependencies(pkg, cfg['test_file'])
        else:
            deps = get_dependencies(pkg, cfg['repo_url'])
            
        graph[pkg] = deps
        
        # Добавляем детей в стек для дальнейшего обхода
        for dep in deps:
            if dep not in visited:
                stack.append((dep, depth + 1))
                
    return graph

def get_test_dependencies(pkg, filepath):
    """Читает граф из текстового файла для режима тестирования"""
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if ":" in line:
                name, deps_str = line.strip().split(":")
                if name.strip() == pkg:
                    return [d.strip() for d in deps_str.split(",") if d.strip()]
    return []

# ==========================================
# ЭТАП 4: Обратные зависимости
# ==========================================
def get_reverse_dependencies(graph, target_pkg):
    reverse = []
    for pkg, deps in graph.items():
        if target_pkg in deps:
            reverse.append(pkg)
    return reverse

# ==========================================
# ЭТАП 5: Визуализация (Graphviz -> SVG)
# ==========================================
def visualize(graph, output_file):
    dot = Digraph(comment='Граф зависимостей', format='svg')
    
    for pkg, deps in graph.items():
        dot.node(pkg, pkg)
        for dep in deps:
            if dep in graph:
                dot.edge(pkg, dep)
                
    # Сохраняем в SVG
    dot.render(output_file.split('.')[0], cleanup=True)
    print(f"\nИзображение сохранено в {output_file}")

# ==========================================
# ЗАПУСК
# ==========================================
if __name__ == "__main__":
    try:
        cfg = load_config()
        
        print(f"\nАнализ пакета: {cfg['package_name']}...")
        graph = build_graph(cfg['package_name'], cfg)
        
        # Вывод прямых зависимостей (Этап 2)
        print(f"\n--- Прямые зависимости {cfg['package_name']} ---")
        print(graph.get(cfg['package_name'], "Нет зависимостей"))
        
        # Вывод обратных зависимостей (Этап 4)
        print(f"\n--- Обратные зависимости для {cfg['package_name']} ---")
        print(get_reverse_dependencies(graph, cfg['package_name']))
        
        # Визуализация (Этап 5)
        visualize(graph, cfg['output_file'])
        
    except Exception as e:
        print(f"Ошибка: {e}")
