
import os
import random
from pathlib import Path
from typing import Dict, List
import torch
from diffusers import ZImagePipeline
from PIL import Image
from tqdm.auto import tqdm

# ============================================================================
# CONFIGURATION
# ============================================================================

# 23 visually distinct refrigerator ingredient classes
INGREDIENT_CLASSES = [
    "milk",             # 0: White liquid in bottle/carton
    "eggs",             # 1: Oval, white/brown in carton
    "cheese",           # 2: Yellow/orange, rectangular block
    "yogurt",           # 3: Large yogurt tub/container
    "butter",           # 4: Yellow, rectangular in wrapper
    "waterbottle",      # 5: Transparent/blue container
    "soda",             # 6: Carbonated beverage can/bottle
    "juice",            # 7: Fruit juice carton/bottle
    "tomato",           # 8: Red, round, smooth
    "cucumber",         # 9: Long, green, cylindrical
    "pepper",           # 10: Bell pepper, various colors
    "apple",            # 11: Round, red/green
    "orange",           # 12: Round, orange, textured skin
    "lemon",            # 13: Yellow, oval, textured
    "salami",           # 14: Cured meat, cylindrical
    "sausage",          # 15: Processed meat links
    "chicken",          # 16: Chicken meat, packaged
    "fish",             # 17: Fish fillet/whole fish
    "cake",             # 18: Sweet dessert, various shapes
    "chocolate",        # 19: Brown confection bar/box
    "lettuce",          # 20: Green, leafy, large
    "carrot",           # 21: Orange, long, tapered
    "banana",           # 22: Yellow, curved fruit
]

# ============================================================================
# CLASS-SPECIFIC VISUAL DESCRIPTIONS
# Detailed visual attributes for each ingredient class (for image generation)
# ============================================================================

CLASS_VISUAL_DESCRIPTIONS = {
    # ═══════════════════════════════════════════════════════════════════════
    # DAIRY PRODUCTS - White/yellow, packaged items
    # ═══════════════════════════════════════════════════════════════════════
    "milk": {
        "color": "white",
        "shape": "tall rectangular carton or plastic gallon jug",
        "texture": "smooth plastic or cardboard",
        "features": "cap on top, brand label, often translucent",
        "prompt": "white plastic milk bottle with blue cap, gallon of milk, milk carton"
    },
    "eggs": {
        "color": "white or brown",
        "shape": "oval eggs arranged in cardboard carton",
        "texture": "smooth shell with slight granular surface",
        "features": "6 or 12 eggs in foam or cardboard tray",
        "prompt": "brown eggs in cardboard carton, white chicken eggs, open egg carton"
    },
    "cheese": {
        "color": "yellow or orange",
        "shape": "rectangular block or triangular wedge",
        "texture": "smooth or with holes (swiss)",
        "features": "plastic wrap or wax coating",
        "prompt": "yellow cheddar cheese block, orange cheese wedge, sliced cheese package"
    },
    "yogurt": {
        "color": "white container with colorful label",
        "shape": "cylindrical cup with foil lid",
        "texture": "smooth plastic container",
        "features": "pull-tab foil seal, brand label",
        "prompt": "white yogurt cup with lid, Greek yogurt container, plastic yogurt tub"
    },
    "butter": {
        "color": "yellow",
        "shape": "rectangular stick",
        "texture": "smooth, wrapped in paper or foil",
        "features": "paper wrapper with brand, often in box",
        "prompt": "yellow butter stick in paper wrapper, butter block, margarine tub"
    },
    
    # ═══════════════════════════════════════════════════════════════════════
    # BEVERAGES - Bottles, cans, cartons
    # ═══════════════════════════════════════════════════════════════════════
    "waterbottle": {
        "color": "clear/transparent or light blue",
        "shape": "tall cylindrical bottle with cap",
        "texture": "smooth plastic, transparent",
        "features": "screw cap, label, you can see water inside",
        "prompt": "clear plastic water bottle, transparent water bottle, mineral water bottle"
    },
    "soda": {
        "color": "red, blue, silver (can colors)",
        "shape": "cylindrical aluminum can or plastic bottle",
        "texture": "metallic shiny surface with printed graphics",
        "features": "pull-tab top, brand logo (Coca-Cola, Pepsi style)",
        "prompt": "aluminum soda can, cola can, red carbonated drink can, soda bottle"
    },
    "juice": {
        "color": "orange, yellow, purple (based on fruit)",
        "shape": "rectangular carton or plastic bottle",
        "texture": "cardboard carton or plastic",
        "features": "screw cap, fruit images on label",
        "prompt": "orange juice carton, fruit juice box, apple juice bottle, juice container"
    },
    
    # ═══════════════════════════════════════════════════════════════════════
    # VEGETABLES - Fresh produce
    # ═══════════════════════════════════════════════════════════════════════
    "tomato": {
        "color": "bright red (ripe) or green (unripe)",
        "shape": "round, slightly flattened sphere",
        "texture": "smooth, shiny skin",
        "features": "green stem on top, natural shine",
        "prompt": "red ripe tomato, round fresh tomato, cherry tomatoes, tomato on vine"
    },
    "cucumber": {
        "color": "dark green",
        "shape": "long cylindrical",
        "texture": "bumpy skin with small ridges",
        "features": "tapered ends, uniform dark green color",
        "prompt": "long green cucumber, fresh whole cucumber, English cucumber"
    },
    "pepper": {
        "color": "red, green, yellow, or orange",
        "shape": "bell-shaped with lobes at bottom",
        "texture": "smooth, shiny, waxy skin",
        "features": "green stem on top, hollow inside",
        "prompt": "red bell pepper, green bell pepper, yellow capsicum, colorful peppers"
    },
    "lettuce": {
        "color": "light green to dark green",
        "shape": "large leafy head, round/oval",
        "texture": "crisp leaves with visible veins",
        "features": "layered leaves, ruffled edges",
        "prompt": "green iceberg lettuce, leafy romaine lettuce, fresh lettuce head"
    },
    "carrot": {
        "color": "bright orange",
        "shape": "long tapered cone",
        "texture": "smooth with horizontal ridges",
        "features": "green leafy top (optional), pointed tip",
        "prompt": "orange carrot, fresh carrots with greens, baby carrots, carrot sticks"
    },
    
    # ═══════════════════════════════════════════════════════════════════════
    # FRUITS - Fresh produce
    # ═══════════════════════════════════════════════════════════════════════
    "apple": {
        "color": "red, green, or yellow",
        "shape": "round with slight indent at top/bottom",
        "texture": "smooth, shiny, waxy skin",
        "features": "small stem on top, natural shine",
        "prompt": "red apple, green Granny Smith apple, fresh shiny apple"
    },
    "orange": {
        "color": "bright orange",
        "shape": "round sphere",
        "texture": "dimpled, pitted peel (peau d'orange)",
        "features": "navel at bottom, slight green near stem",
        "prompt": "orange citrus fruit, navel orange, mandarin, fresh orange"
    },
    "lemon": {
        "color": "bright yellow",
        "shape": "oval with pointed ends",
        "texture": "dimpled peel similar to orange",
        "features": "pointed tips on both ends, vibrant yellow",
        "prompt": "yellow lemon, fresh lemon citrus, whole lemon fruit"
    },
    "banana": {
        "color": "yellow (ripe) with brown spots when very ripe",
        "shape": "curved elongated",
        "texture": "smooth peel",
        "features": "bunch of 4-6 bananas, brown stem",
        "prompt": "yellow banana, ripe banana bunch, fresh bananas"
    },
    
    # ═══════════════════════════════════════════════════════════════════════
    # MEAT & PROTEIN - Packaged items
    # ═══════════════════════════════════════════════════════════════════════
    "salami": {
        "color": "dark red with white fat spots",
        "shape": "circular slices or cylindrical stick",
        "texture": "marbled meat with visible fat",
        "features": "casing on stick form, sliced rounds",
        "prompt": "sliced salami, pepperoni slices, cured deli meat, salami stick"
    },
    "sausage": {
        "color": "pink/brown",
        "shape": "cylindrical links connected together",
        "texture": "smooth casing",
        "features": "twisted links, often in pairs or chains",
        "prompt": "pork sausage links, breakfast sausages, hot dogs, frankfurters"
    },
    "chicken": {
        "color": "pale pink/beige",
        "shape": "irregular meat pieces",
        "texture": "raw meat texture visible through plastic",
        "features": "in plastic wrap or styrofoam tray",
        "prompt": "packaged chicken breast, raw chicken in tray, chicken thighs package"
    },
    "fish": {
        "color": "pink (salmon) or white (cod)",
        "shape": "flat fillet or whole fish shape",
        "texture": "visible muscle striations",
        "features": "in plastic wrap, may show scales on whole fish",
        "prompt": "fish fillet, salmon fillet, white fish package, fresh fish in tray"
    },
    
    # ═══════════════════════════════════════════════════════════════════════
    # SWEETS & DESSERTS
    # ═══════════════════════════════════════════════════════════════════════
    "cake": {
        "color": "brown (chocolate), white (vanilla), colorful frosting",
        "shape": "round or rectangular, sliced wedge",
        "texture": "fluffy sponge with smooth frosting",
        "features": "layers visible in slice, decorations on top",
        "prompt": "slice of chocolate cake, birthday cake in fridge, frosted layer cake"
    },
    "chocolate": {
        "color": "dark brown or milk brown",
        "shape": "rectangular bar with segments or box",
        "texture": "smooth, glossy surface",
        "features": "wrapper partially visible, brand name",
        "prompt": "chocolate bar, chocolate box, milk chocolate, dark chocolate bar"
    },
}

# ============================================================================
# SCENARIO-BASED PROMPT TEMPLATES (YOLO Optimized)
# ============================================================================


# A. GENERAL/BALANCED SCENARIOS (60% of data)
# Standard fridge views with professional camera specs (f/8, 24mm, volumetric lighting)
GENERAL_PROMPTS = [
    # Eye-level standard view - Technical camera specs from report
    "Photorealistic photo of open refrigerator interior with {ingredients}, shot with 24mm wide angle lens, f/8 deep depth of field, volumetric LED lighting, hyperrealistic, 8k quality, professional food photography",
    "Inside an open fridge showing {ingredients} arranged naturally on glass shelves, soft volumetric LED lighting, realistic home kitchen, f/8 aperture sharp focus throughout, reflections on surfaces, photorealistic",
    "Refrigerator interior photograph with {ingredients} on white glass shelves, 24mm wide angle perspective, f/8 deep focus, bright interior LED light, professional product photography, hyperrealistic details",
    # High-angle view (security camera perspective)
    "High-angle security camera view looking down into open refrigerator with {ingredients} visible on shelves below, wide angle 24mm, f/8 aperture, volumetric LED lighting, photorealistic, natural arrangement",
    "Top-down angled shot of fridge shelves containing {ingredients}, 24mm lens, f/8 sharp focus, reflections on glass shelves, volumetric lighting from above, hyperrealistic",
    # Door shelf view with reflections
    "Open refrigerator door shelf with {ingredients} in door compartments and main shelves visible, 24mm wide angle, f/8 deep DOF, realistic reflections, volumetric LED lighting, photorealistic, 8k",
]

# B. CHALLENGING/COMPLEX SCENARIOS (25% of data)
# Messy, crowded, occlusion, shadows - pushes model limits (with technical specs)
CHALLENGING_PROMPTS = [
    # Heavy occlusion (>70% occlusion handling from report)
    "Messy refrigerator interior, crowded shelves packed with {ingredients}, objects overlapping and partially hidden behind each other, 24mm lens, f/8 deep focus, realistic occlusion, harsh LED shadows, photorealistic",
    "Stuffed fridge with {ingredients} crammed together, items blocking each other, only partial views of some objects, wide angle 24mm, f/8 aperture, dim volumetric lighting in back, hyperrealistic",
    # Dim/shadow lighting (HDRI night condition)
    "Dimly lit refrigerator interior at night with {ingredients} visible, HDRI night lighting, some items in shadow, 24mm lens, f/8 aperture, realistic low-light scenario, photorealistic",
    "Open fridge with {ingredients}, harsh shadows from single LED source, dark corners, fluorescent kitchen background, 24mm wide angle, f/8, realistic lighting contrast, hyperrealistic",
    # Very crowded (density-based terms from report)
    "Overflowing refrigerator bursting with {ingredients}, cluttered arrangement, items stacked on each other, 24mm lens, f/8 deep DOF, volumetric LED lighting, photorealistic overstuffed fridge",
    "Packed fridge shelves with {ingredients} squeezed together, sparse to cluttered gradient, multiple items per shelf, 24mm, f/8, bright volumetric lighting, hyperrealistic family fridge",
    # Mixed angles and mess with different materials
    "Disorganized fridge interior with {ingredients} placed haphazardly, stainless steel interior, some items tilted, 24mm wide angle, f/8, uneven LED lighting, reflections on metal surfaces, photorealistic",
    # Frosted/condensation challenge
    "Refrigerator with condensation droplets on glass shelves, {ingredients} visible through foggy surfaces, 24mm lens, f/8, cool volumetric lighting, hyperrealistic moisture effects",
]

# C. RARE CLASS FOCUSED SCENARIOS (5% of data)
# Close-ups of small/rare items that need extra training examples
RARECLASS_PROMPTS = [
    "Close-up shot of refrigerator door shelf containing {ingredient} in clear focus, 50mm macro lens, f/2.8 shallow depth of field, detailed texture visible, volumetric LED lighting, photorealistic macro view, 8k",
    "Detailed macro view of {ingredient} on fridge glass shelf, 50mm lens, f/2.8, sharp focus on the item, surrounding items naturally blurred, realistic product photography, hyperrealistic",
    "Refrigerator shelf close-up featuring {ingredient} prominently in center, macro photography, f/2.8, high detail, crisp focus, professional volumetric lighting, photorealistic",
    "{ingredient} on glass fridge shelf, eye-level macro view, 50mm lens, f/2.8, realistic texture and color, soft background blur, volumetric LED lighting, hyperrealistic",
]

# D. TRANSITION STATES - DOOR POSITIONS (5% of data)
# Partially open doors for interaction robustness (from report: 10°, 30°, 45°)
TRANSITION_PROMPTS = [
    "Refrigerator door partially open at 10 degrees angle, glimpse of {ingredients} inside, 24mm wide angle, f/8, volumetric LED light spilling out, realistic kitchen background, photorealistic",
    "Fridge door half-open at 30 degrees showing {ingredients} on shelves inside, 24mm lens, f/8 deep focus, warm kitchen lighting mixing with cold fridge LED, hyperrealistic",
    "Refrigerator with door open at 45 degrees, {ingredients} visible through gap, 24mm wide angle, f/8, contrast between warm room and cool interior lighting, photorealistic",
    "Person's hand opening fridge door at 30 degrees, {ingredients} partially visible inside, 24mm, f/8, action shot, volumetric lighting, realistic motion, hyperrealistic",
    "Kitchen scene with refrigerator door ajar at 10 degrees, {ingredients} glimpse inside, wide angle 24mm, f/8, daylight HDRI from window, mixed lighting, photorealistic",
]

# EMPTY REFRIGERATOR TEMPLATES (for background-only images - 0-10% from report, reduces false positives!)
EMPTY_FRIDGE_TEMPLATES = [
    "Empty refrigerator interior, clean white glass shelves, cold blue volumetric LED lighting, 24mm wide angle, f/8, hyperrealistic, no food, no bottles, no items, completely empty fridge, 8k",
    "Inside of modern empty fridge, multiple glass shelves, chrome door shelves, bright interior LED light, 24mm lens, f/8 deep focus, photorealistic, empty, no products, clean and organized",
    "Refrigerator interior view, empty clean shelves, wire rack, white walls, condensation on walls, volumetric LED light, 24mm, f/8, photorealistic, completely empty, no objects",
    "Open modern refrigerator, empty glass shelves, stainless steel interior, cold atmosphere, 24mm wide angle, f/8, volumetric lighting, no food, no containers, hyperrealistic pristine condition",
    "Empty fridge inside, slightly frosted interior, single LED light, wire shelves, 24mm lens, f/8, photorealistic, no items, no bottles, totally empty",
    # Domain randomization: different fridge types/conditions
    "Empty but dirty refrigerator interior, stained shelves, water marks, no food items, 24mm, f/8, photorealistic old fridge, dim LED lighting",
    "Empty refrigerator with condensation droplets on walls, foggy glass shelves, no items inside, 24mm lens, f/8, cold volumetric atmosphere, hyperrealistic",
    "Empty vintage refrigerator, yellowed plastic shelves, old style, no food, 24mm wide angle, f/8, photorealistic retro style, completely empty",
    "Empty commercial refrigerator, industrial metal shelves, no products, 24mm, f/8, bright fluorescent lighting, hyperrealistic, stainless steel interior",
]

# Negative prompts - Based on Synthetic_Data_Summary.md recommendations
# Essential negatives: cartoon, illustration, blurry, bad geometry, distorted, watermark
# Added: robots, devices, appliances, unknown products to prevent random objects
# Added: grapes, cherries, sliced items, plates, raw meat to prevent hallucinations
BASE_NEGATIVE_PROMPT = "cartoon, anime, drawing, painting, sketch, illustration, render, cgi, 3d, unrealistic, fake, blurry, blur, unfocused, out of focus, low quality, bad quality, poor quality, low resolution, pixelated, distorted, deformed, disfigured, malformed, mutated, bad geometry, ugly, rotten, spoiled, moldy, watermark, logo, signature, copyright, bokeh, shallow depth of field, robot, vacuum, appliance, device, electronics, machine, floor, ground, kitchen floor, tiles, grapes, grape, cherry, cherries, berries, sliced fruit, sliced apple, cut fruit, plate, dish, bowl, platter, raw meat, raw chicken, unpackaged meat, strawberry, raspberry, blueberry, peach, pear, banana, pineapple"

# For general scenarios - deep DOF, no bokeh (f/8 from report)
GENERAL_NEGATIVE_PROMPT = BASE_NEGATIVE_PROMPT + ", floating objects, objects merged together, impossible physics, hybrid fruits, wrong perspective, random objects, unknown items, unrecognized products"

# For challenging scenarios - minimal restrictions to allow messy/crowded
CHALLENGING_NEGATIVE_PROMPT = BASE_NEGATIVE_PROMPT + ", floating objects, impossible physics, merged objects, wrong proportions, random objects, unknown items"

# For rare class close-ups - want sharp focus on subject (different aperture allowed)
RARECLASS_NEGATIVE_PROMPT = "cartoon, anime, drawing, painting, sketch, illustration, render, cgi, 3d, unrealistic, fake, low quality, bad quality, pixelated, distorted, deformed, watermark, logo, blurry subject, out of focus subject, cluttered, too many objects, robot, vacuum, appliance, device"

# For transition states - door positions
TRANSITION_NEGATIVE_PROMPT = BASE_NEGATIVE_PROMPT + ", closed door, fully open door, floating objects, wrong perspective, impossible angle, robot, vacuum"

# Extra negative prompt for empty fridge (ensure no food!)
EMPTY_NEGATIVE_PROMPT = BASE_NEGATIVE_PROMPT + ", food, vegetables, fruits, bottles, jars, containers, cans, meat, dairy, drinks, beverages, packages, boxes, cartons, eggs, cheese, milk, products, items, objects"

# Generation settings for YOLO training (Based on Synthetic_Data_Summary.md)
# Recommended: ≥1,500 images/class, ≥10,000 instances/class
TOTAL_IMAGES = 35000   # 35k for 21 classes = ~1,666 images/class
MIN_OBJECTS_PER_IMAGE = 5   # YOLO loves crowded scenes!
MAX_OBJECTS_PER_IMAGE = 15  # Up to 15 objects per image (more instances)

# Scenario distribution (CRITICAL for model generalization)
GENERAL_SCENARIO_RATIO = 0.60    # 60% standard balanced scenarios
CHALLENGING_SCENARIO_RATIO = 0.25  # 25% messy, crowded, occlusion
RARECLASS_SCENARIO_RATIO = 0.05   # 5% close-up rare items (honey, olive, butter)
BACKGROUND_ONLY_RATIO = 0.05      # 5% empty images (0-10% from report, reduces false positives)
TRANSITION_SCENARIO_RATIO = 0.05  # 5% door transition states (10°, 30°, 45°)

# Rare/small classes that need extra attention (Targeted Data Generation from report)
RARE_CLASSES = ["fish", "salami", "sausage", "chocolate"]

# Training strategy ratios (from report: 80% synthetic / 20% real recommended)
TRAIN_RATIO = 0.7      # 70% for training  
VAL_RATIO = 0.15       # 15% for validation
TEST_RATIO = 0.15      # 15% for testing

# Image dimensions - VERTICAL aspect ratio for fridges (9:16 from report)
# rect=True training recommended for vertical images
IMAGE_WIDTH = 720      # 9:16 vertical aspect ratio
IMAGE_HEIGHT = 1280    # Higher resolution (1280) for small object detection as per report
GUIDANCE_SCALE = 0.0   # Must be 0.0 for Z-Image-Turbo (CRITICAL!)
NUM_INFERENCE_STEPS = 6 # Z-Image-Turbo optimized for 8 NFEs (9 steps = 8 forwards)

# Model configuration
MODEL_NAME = "Tongyi-MAI/Z-Image-Turbo"

# Google Drive paths
DRIVE_BASE_PATH = "/content/drive/MyDrive/refrigerator_yolo_dataset"
ANNOTATIONS_PATH = "/content/drive/MyDrive/refrigerator_yolo_dataset/labels"  # For future YOLO annotations

# ============================================================================
# SETUP FUNCTIONS
# ============================================================================

def create_directory_structure(base_path: str) -> Dict[str, str]:
    """Create YOLO-style directory structure (images + labels)"""
    print(f"\n📂 Creating YOLO directory structure at {base_path}...")
    
    splits = ["train", "val", "test"]
    paths = {}
    
    for split in splits:
        # Create images directory
        img_dir = os.path.join(base_path, "images", split)
        os.makedirs(img_dir, exist_ok=True)
        paths[f"images/{split}"] = img_dir
        
        # Create labels directory (for future annotations)
        label_dir = os.path.join(base_path, "labels", split)
        os.makedirs(label_dir, exist_ok=True)
        paths[f"labels/{split}"] = label_dir
    
    print(f"✅ Created YOLO directory structure (images + labels)")
    return paths


def create_balanced_image_plan(total_images: int) -> List[Dict]:
    """
    Create scenario-based image generation plan for YOLO training.
    Based on Synthetic_Data_Summary.md recommendations.
    
    Scenario Distribution:
    - 60% General/Balanced (standard fridge views with technical camera specs)
    - 25% Challenging (messy, crowded, occlusion, shadows, domain randomization)
    - 5% Rare class focused (close-ups of honey, olive, butter, etc.)
    - 5% Background only (empty fridge - 0-10% from report, reduces false positives)
    - 5% Transition states (partially open doors: 10°, 30°, 45°)
    
    Returns list of dicts with format:
    {"image_id": 0, "split": "train", "ingredients": [...], "scenario": "general/challenging/rareclass/background/transition"}
    """
    print("\n📊 Creating YOLO-optimized scenario distribution plan...")
    print("📋 Based on Synthetic_Data_Summary.md recommendations:")
    print("   - ≥1,500 images per class")
    print("   - ≥10,000 instances per class")
    print("   - Vertical aspect ratio (9:16) for tall fridge images")
    print("   - rect=True training recommended")
    
    # Calculate scenario distribution
    general_images = int(total_images * GENERAL_SCENARIO_RATIO)
    challenging_images = int(total_images * CHALLENGING_SCENARIO_RATIO)
    rareclass_images = int(total_images * RARECLASS_SCENARIO_RATIO)
    background_images = int(total_images * BACKGROUND_ONLY_RATIO)
    transition_images = int(total_images * TRANSITION_SCENARIO_RATIO)
    
    # Adjust to match total
    remaining = total_images - (general_images + challenging_images + rareclass_images + background_images + transition_images)
    general_images += remaining
    
    print(f"\nTotal images: {total_images}")
    print(f"  📗 General scenarios: {general_images} ({general_images/total_images:.0%})")
    print(f"  📙 Challenging scenarios: {challenging_images} ({challenging_images/total_images:.0%})")
    print(f"  📕 Rare class close-ups: {rareclass_images} ({rareclass_images/total_images:.0%})")
    print(f"  ⬜ Background only: {background_images} ({background_images/total_images:.0%})")
    print(f"  🚪 Transition states: {transition_images} ({transition_images/total_images:.0%})")
    
    # Track class appearances for balancing
    class_counter = {cls: 0 for cls in INGREDIENT_CLASSES}
    image_plan = []
    
    # Determine splits
    train_size = int(total_images * TRAIN_RATIO)
    val_size = int(total_images * VAL_RATIO)
    splits = (["train"] * train_size + 
              ["val"] * val_size + 
              ["test"] * (total_images - train_size - val_size))
    random.shuffle(splits)
    
    img_id = 0
    
    # 1. Background-only images (empty refrigerator)
    for _ in range(background_images):
        image_plan.append({
            "image_id": img_id,
            "split": splits[img_id],
            "ingredients": [],
            "scenario": "background"
        })
        img_id += 1
    
    # 2. Rare class focused images (close-ups)
    for _ in range(rareclass_images):
        # Pick a rare class, preferring least-used ones
        rare_counts = {cls: class_counter[cls] for cls in RARE_CLASSES}
        selected_class = min(rare_counts, key=rare_counts.get)
        class_counter[selected_class] += 3  # Close-ups count as 3 instances (prominent)
        
        image_plan.append({
            "image_id": img_id,
            "split": splits[img_id],
            "ingredients": [selected_class],
            "scenario": "rareclass"
        })
        img_id += 1
    
    # 3. Transition states (partially open doors: 10°, 30°, 45°)
    for _ in range(transition_images):
        # Moderate number of objects visible through gap
        num_objects = random.randint(3, 8)
        
        sorted_classes = sorted(class_counter.items(), key=lambda x: (x[1], random.random()))
        
        selected = []
        for cls, count in sorted_classes:
            if len(selected) >= num_objects:
                break
            selected.append(cls)
            class_counter[cls] += 1
        
        image_plan.append({
            "image_id": img_id,
            "split": splits[img_id],
            "ingredients": selected,
            "scenario": "transition"
        })
        img_id += 1
    
    # 4. Challenging scenarios (messy, crowded, occlusion)
    for _ in range(challenging_images):
        # More objects for challenging scenes (8-15+)
        num_objects = random.randint(8, MAX_OBJECTS_PER_IMAGE + 3)
        num_objects = min(num_objects, len(INGREDIENT_CLASSES))
        
        # Select ingredients with lowest appearance count (greedy balancing)
        sorted_classes = sorted(class_counter.items(), key=lambda x: (x[1], random.random()))
        
        selected = []
        for cls, count in sorted_classes:
            if len(selected) >= num_objects:
                break
            selected.append(cls)
            class_counter[cls] += 1
        
        image_plan.append({
            "image_id": img_id,
            "split": splits[img_id],
            "ingredients": selected,
            "scenario": "challenging"
        })
        img_id += 1
    
    # 5. General/balanced scenarios (standard)
    for _ in range(general_images):
        num_objects = random.randint(MIN_OBJECTS_PER_IMAGE, MAX_OBJECTS_PER_IMAGE)
        
        # Select ingredients with lowest appearance count
        sorted_classes = sorted(class_counter.items(), key=lambda x: (x[1], random.random()))
        
        selected = []
        for cls, count in sorted_classes:
            if len(selected) >= num_objects:
                break
            selected.append(cls)
            class_counter[cls] += 1
        
        image_plan.append({
            "image_id": img_id,
            "split": splits[img_id],
            "ingredients": selected,
            "scenario": "general"
        })
        img_id += 1
    
    # Shuffle to mix scenarios
    random.shuffle(image_plan)
    for i, plan in enumerate(image_plan):
        plan["image_id"] = i
        plan["split"] = splits[i]
    
    # Print class distribution stats (target from report: ≥10,000 instances/class)
    print(f"\n📈 Class instance distribution:")
    counts = list(class_counter.values())
    print(f"  Min instances: {min(counts)} ({min(class_counter, key=class_counter.get)})")
    print(f"  Max instances: {max(counts)} ({max(class_counter, key=class_counter.get)})")
    print(f"  Avg instances: {sum(counts)/len(counts):.1f}")
    print(f"  Total instances: {sum(counts)} (target: ≥10,000 per class)")
    
    # Check if we meet report recommendations
    avg_instances = sum(counts)/len(counts)
    if avg_instances < 10000:
        print(f"  ⚠️  Below recommended 10,000 instances/class. Consider increasing TOTAL_IMAGES.")
    else:
        print(f"  ✅ Meets recommended ≥10,000 instances/class!")
    
    # Check rare classes
    print(f"\n🔍 Rare class instances (Targeted Data Generation):")
    for cls in RARE_CLASSES:
        print(f"  {cls}: {class_counter[cls]}")
    
    return image_plan


# ============================================================================
# IMAGE GENERATION
# ============================================================================

def load_model():
    """Load the diffusion model"""
    print(f"\n🤖 Loading model: {MODEL_NAME}")
    print("This may take a few minutes on first run...")
    
    # Z-Image-Turbo uses bfloat16 for optimal performance
    pipe = ZImagePipeline.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
    )
    
    # Move to GPU
    if torch.cuda.is_available():
        pipe = pipe.to("cuda")
        print(f"✅ Model loaded on GPU: {torch.cuda.get_device_name(0)}")
        print(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    else:
        print("⚠️ GPU not available, using CPU (will be slower)")
    
    return pipe


def format_ingredients_text(ingredients: List[str]) -> str:
    """Format ingredient list as natural language"""
    if len(ingredients) == 1:
        return ingredients[0]
    elif len(ingredients) == 2:
        return f"{ingredients[0]} and {ingredients[1]}"
    else:
        return ", ".join(ingredients[:-1]) + f", and {ingredients[-1]}"


def generate_image(pipe, ingredients: List[str], scenario: str = "general") -> Image.Image:
    """
    Generate image based on scenario type.
    All prompts include technical camera specs from Synthetic_Data_Summary.md:
    - f/8 deep DOF (general scenes)
    - 24mm wide angle (perspective)
    - Volumetric lighting
    - Vertical aspect ratio (9:16)
    
    Scenarios:
    - background: Empty refrigerator (no food)
    - rareclass: Close-up of single rare item (f/2.8 macro)
    - challenging: Messy, crowded, occlusion
    - transition: Partially open doors (10°, 30°, 45°)
    - general: Standard balanced fridge view
    """
    
    # 1. BACKGROUND ONLY - Empty fridge
    if scenario == "background" or not ingredients:
        prompt = random.choice(EMPTY_FRIDGE_TEMPLATES)
        neg_prompt = EMPTY_NEGATIVE_PROMPT
    
    # 2. RARE CLASS - Close-up shot (macro lens)
    elif scenario == "rareclass":
        ingredient = ingredients[0]  # Single rare item
        prompt_template = random.choice(RARECLASS_PROMPTS)
        prompt = prompt_template.format(ingredient=ingredient)
        neg_prompt = RARECLASS_NEGATIVE_PROMPT
    
    # 3. TRANSITION - Partially open doors
    elif scenario == "transition":
        ingredient_text = format_ingredients_text(ingredients)
        prompt_template = random.choice(TRANSITION_PROMPTS)
        prompt = prompt_template.format(ingredients=ingredient_text)
        neg_prompt = TRANSITION_NEGATIVE_PROMPT
    
    # 4. CHALLENGING - Messy, crowded, occlusion
    elif scenario == "challenging":
        ingredient_text = format_ingredients_text(ingredients)
        prompt_template = random.choice(CHALLENGING_PROMPTS)
        prompt = prompt_template.format(ingredients=ingredient_text)
        neg_prompt = CHALLENGING_NEGATIVE_PROMPT
    
    # 5. GENERAL - Standard balanced view (default)
    else:  # general
        ingredient_text = format_ingredients_text(ingredients)
        prompt_template = random.choice(GENERAL_PROMPTS)
        prompt = prompt_template.format(ingredients=ingredient_text)
        neg_prompt = GENERAL_NEGATIVE_PROMPT
    
    # Generate image with VERTICAL aspect ratio (9:16 from report)
    # Fridges are tall - rect=True training recommended
    image = pipe(
        prompt=prompt,
        negative_prompt=neg_prompt,
        num_inference_steps=NUM_INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        height=IMAGE_HEIGHT,  # 1280 - tall (9:16 vertical)
        width=IMAGE_WIDTH,    # 720 - narrower
    ).images[0]
    
    return image


def get_next_image_id(base_path: str) -> int:
    """Find the highest existing image ID and return the next one"""
    import glob
    max_id = -1
    
    # Check all splits for existing images
    for split in ["train", "val", "test"]:
        pattern = os.path.join(base_path, "images", split, "img_*.jpg")
        existing_files = glob.glob(pattern)
        
        for filepath in existing_files:
            filename = os.path.basename(filepath)
            # Extract ID from img_00123.jpg format
            try:
                img_id = int(filename.replace("img_", "").replace(".jpg", ""))
                if img_id > max_id:
                    max_id = img_id
            except ValueError:
                continue
    
    next_id = max_id + 1
    if next_id > 0:
        print(f"📂 Found existing images, continuing from ID: {next_id}")
    return next_id


def generate_dataset(pipe, base_path: str):
    """Generate scenario-based dataset for YOLO training (optimized per Synthetic_Data_Summary.md)"""
    print(f"\n🎨 Starting YOLO dataset generation...")
    print(f"📋 Optimized settings from Synthetic_Data_Summary.md:")
    print(f"   - Vertical aspect ratio: {IMAGE_WIDTH}x{IMAGE_HEIGHT} (9:16)")
    print(f"   - rect=True training recommended")
    print(f"   - Technical camera specs: f/8, 24mm, volumetric lighting")
    print(f"Classes: {len(INGREDIENT_CLASSES)}")
    print(f"Total images: {TOTAL_IMAGES}")
    print(f"Objects per image: {MIN_OBJECTS_PER_IMAGE}-{MAX_OBJECTS_PER_IMAGE}")
    print(f"Split: {TRAIN_RATIO:.0%} train / {VAL_RATIO:.0%} val / {TEST_RATIO:.0%} test\n")
    
    # Get starting image ID (continues from existing images)
    start_id = get_next_image_id(base_path)
    
    # Create scenario-based image plan
    image_plan = create_balanced_image_plan(TOTAL_IMAGES)
    
    # Generate images
    progress_bar = tqdm(total=len(image_plan), desc="Generating images")
    stats = {"train": 0, "val": 0, "test": 0}
    scenario_stats = {"general": 0, "challenging": 0, "rareclass": 0, "background": 0, "transition": 0}
    metadata = []
    
    for plan in image_plan:
        img_id = plan["image_id"] + start_id
        split = plan["split"]
        ingredients = plan["ingredients"]
        scenario = plan.get("scenario", "general")
        
        # Update progress description
        scenario_emoji = {"general": "📗", "challenging": "📙", "rareclass": "📕", "background": "⬜", "transition": "🚪"}
        if scenario == "background":
            ing_text = "EMPTY"
        else:
            ing_text = f"{len(ingredients)} items"
        progress_bar.set_description(f"{scenario_emoji.get(scenario, '📗')} {scenario}: {ing_text}")
        try:
            # Generate image based on scenario
            image = generate_image(pipe, ingredients, scenario)
            
            # Save image
            filename = f"img_{img_id:05d}.jpg"
            save_path = os.path.join(base_path, "images", split, filename)
            image.save(save_path, quality=95)
            
            # Create empty label file for background images
            if scenario == "background":
                label_filename = f"img_{img_id:05d}.txt"
                label_path = os.path.join(base_path, "labels", split, label_filename)
                with open(label_path, 'w') as f:
                    pass  # Empty file - no objects!
            
            # Save metadata
            metadata.append({
                "image_id": img_id,
                "filename": filename,
                "split": split,
                "ingredients": ingredients,
                "num_objects": len(ingredients),
                "scenario": scenario
            })
            
            stats[split] += 1
            scenario_stats[scenario] += 1
            
            # Clear CUDA cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
        except Exception as e:
            print(f"\n❌ Error generating image {img_id}: {e}")
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            continue
        
        progress_bar.update(1)
    
    progress_bar.close()
    
    # Save metadata as JSON
    import json
    metadata_path = os.path.join(base_path, "dataset_metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Save class names file
    classes_path = os.path.join(base_path, "classes.txt")
    with open(classes_path, 'w') as f:
        for cls in INGREDIENT_CLASSES:
            f.write(f"{cls}\n")
    
    print("\n" + "="*60)
    print("✅ Dataset generation complete!")
    print("="*60)
    print(f"\n📊 Split Statistics:")
    print(f"  Train: {stats['train']} | Val: {stats['val']} | Test: {stats['test']}")
    print(f"  Total: {sum(stats.values())}")
    print(f"\n🎬 Scenario Statistics:")
    print(f"  📗 General (60%): {scenario_stats['general']}")
    print(f"  📙 Challenging (25%): {scenario_stats['challenging']}")
    print(f"  📕 Rare class (5%): {scenario_stats['rareclass']}")
    print(f"  ⬜ Background (5%): {scenario_stats['background']}")
    print(f"  🚪 Transition (5%): {scenario_stats['transition']}")
    print(f"\n📁 Dataset: {base_path}")
    print(f"📄 Metadata: {metadata_path}")
    print("\n⚠️  NEXT STEP: Run auto_labeler_florence_sam.py for GroundingDINO + SAM labeling")
    print("💡 Background images already have empty .txt label files!")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main execution function - Optimized per Synthetic_Data_Summary.md"""
    print("="*60)
    print("🍅 YOLO REFRIGERATOR INGREDIENT DATASET GENERATOR")
    print("   Optimized per Synthetic_Data_Summary.md recommendations")
    print("="*60)
    print("Scenario-based synthetic data for robust YOLO training")
    print(f"Strategy: {GENERAL_SCENARIO_RATIO:.0%} General | {CHALLENGING_SCENARIO_RATIO:.0%} Challenging | {RARECLASS_SCENARIO_RATIO:.0%} Rare | {BACKGROUND_ONLY_RATIO:.0%} Empty | {TRANSITION_SCENARIO_RATIO:.0%} Transition")
    print(f"Objects per image: {MIN_OBJECTS_PER_IMAGE}-{MAX_OBJECTS_PER_IMAGE}")
    print(f"Image size: {IMAGE_WIDTH}x{IMAGE_HEIGHT} (9:16 vertical - rect=True recommended)")
    print("="*60)
    print("Using: Tongyi-MAI/Z-Image-Turbo (no Qwen needed!)")
    print("="*60)
    
    # Set random seed for reproducibility
    random.seed(42)
    torch.manual_seed(42)
    
    # Create directories
    create_directory_structure(DRIVE_BASE_PATH)
    
    # Load model (Z-Image-Turbo works directly with DiffusionPipeline)
    pipe = load_model()
    
    # Generate dataset
    generate_dataset(pipe, DRIVE_BASE_PATH)
    
    print("\n🎉 Image generation complete!")
    print(f"📂 Location: {DRIVE_BASE_PATH}")
    print("\n" + "="*60)
    print("IMPORTANT: YOLO Training Requirements")
    print("="*60)
    print("✅ Images generated with balanced class distribution")
    print("❌ Bounding box annotations NOT generated (requires separate tool)")
    print("\nAnnotation Options:")
    print("1. Manual: Roboflow (roboflow.com) - easiest for beginners")
    print("2. Manual: CVAT (cvat.org) - professional tool")
    print("3. Auto: GroundingDINO + SAM - AI-powered annotation")
    print("\nYOLO format: labels/train/img_00001.txt with format:")
    print("class_id x_center y_center width height (normalized 0-1)")
    print("="*60)


if __name__ == "__main__":
    main()
