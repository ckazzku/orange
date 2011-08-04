import Orange
import re

data = Orange.data.Table("iris")
tree = Orange.classification.tree.TreeLearner(data, max_depth=3)

def get_margin(dist):
    if dist.abs < 1e-30:
        return 0
    l = list(dist)
    l.sort()
    return (l[-1] - l[-2]) / dist.abs

def replaceB(strg, mo, node, parent, tree):
    margin = get_margin(node.distribution)

    by = mo.group("by")
    if margin and by:
        whom = Orange.classification.tree.byWhom(by, parent, tree)
        if whom and whom.distribution:
            div_margin = get_margin(whom.distribution)
            if div_margin > 1e-30:
                margin /= div_margin
            else:
                Orange.classification.tree.insertDot(strg, mo)
        else:
            return Orange.classification.tree.insertDot(strg, mo)
    return Orange.classification.tree.insertNum(strg, mo, margin)
    
my_format = [(re.compile("%"+Orange.classification.tree.fs
    +"B"+Orange.classification.tree.by), replaceB)]
            
print tree.dump(leaf_str="%V %^B% (%^3.2BbP%)", user_formats=my_format)
