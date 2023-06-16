# Converts a cmake list to a string, which can be interpreted as list content in
# meson configuration file.
# The delimiting brackets are not included.
# Example output: "'foo', 'bar', 'baz'"

function(to_meson_list input_list out_var)
    list(JOIN input_list "', '" input_list)
    set(${out_var} "'${input_list}'" PARENT_SCOPE)
endfunction()
