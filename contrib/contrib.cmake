include(contrib/profiling/clang_rt.profile.cmake)


function(add_contrib_libs directory variant target_triple flags libc_target)
    get_runtimes_flags("${directory}" "${flags}")
    
    add_contrib_lib_profile(${directory} ${variant} ${target_triple} ${flags} ${libc_target})
endfunction()
