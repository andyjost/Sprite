mynot x = fcase x of {True -> False; False -> True}
main = mynot x where x free
