from collections import defaultdict

from .geometry import clip_to_image, iou, is_out_of_bounds

ACCEPT_IOU = 0.9


def by_image(boxes):
    grouped = defaultdict(list)
    for box in boxes:
        grouped[box.image].append(box)
    return grouped


def classify(pre, rev):
    if rev is None:
        return "deleted"
    if rev.label != pre.label:
        return "relabeled"
    return "accepted" if iou(pre, rev) >= ACCEPT_IOU else "adjusted"


def evaluate(images, prelabels, reviews):
    pre_by_image, rev_by_image = by_image(prelabels), by_image(reviews)
    outcomes, added, out_of_bounds = {}, {}, []
    for image_id in sorted(images):
        image = images[image_id]
        pres = clip_to_image(pre_by_image.get(image_id, []), image.width, image.height)
        revs = rev_by_image.get(image_id, [])
        clipped = clip_to_image(revs, image.width, image.height)
        known = {p.box_id for p in pres}
        rev_by_id = {r.box_id: r for r in clipped if r.box_id in known}
        for pre in pres:
            outcomes[f"{image_id}/{pre.box_id}"] = classify(pre, rev_by_id.get(pre.box_id))
        n_added = sum(1 for r in clipped if r.box_id not in known)
        if n_added:
            added[image_id] = n_added
        for rev in revs:
            if is_out_of_bounds(rev, image.width, image.height):
                out_of_bounds.append([image_id, rev.box_id, rev.label])
    return outcomes, added, out_of_bounds
