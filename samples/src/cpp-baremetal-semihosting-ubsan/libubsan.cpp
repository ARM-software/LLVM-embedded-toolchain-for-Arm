#include <stdio.h>
#include <stdlib.h>

extern "C" {
    static void message(const char *msg)
    {
        puts(msg);
    }

    static void message_with_abort(const char *msg)
    {
        puts(msg);
        abort();
    }

    #define HANDLER_RECOVER(name, msg)                      \
    void __ubsan_handle_##name##_minimal() {                \
        message("UBSAN: " msg " (recovered)\n");            \
    }

    #define HANDLER_NORECOVER(name, msg)                    \
    void __ubsan_handle_##name##_minimal_abort() {          \
        message_with_abort("UBSAN: " msg " (aborted)\n");   \
    }

    #define HANDLER(name, msg)                              \
        HANDLER_RECOVER(name, msg)                          \
        HANDLER_NORECOVER(name, msg)                        \

    HANDLER(type_mismatch, "type-mismatch")
    HANDLER(alignment_assumption, "alignment-assumption")
    HANDLER(add_overflow, "add-overflow")
    HANDLER(sub_overflow, "sub-overflow")
    HANDLER(mul_overflow, "mul-overflow")
    HANDLER(negate_overflow, "negate-overflow")
    HANDLER(divrem_overflow, "divrem-overflow")
    HANDLER(shift_out_of_bounds, "shift-out-of-bounds")
    HANDLER(out_of_bounds, "out-of-bounds")
    HANDLER_RECOVER(builtin_unreachable, "builtin-unreachable")
    HANDLER_RECOVER(missing_return, "missing-return")
    HANDLER(vla_bound_not_positive, "vla-bound-not-positive")
    HANDLER(float_cast_overflow, "float-cast-overflow")
    HANDLER(load_invalid_value, "load-invalid-value")
    HANDLER(invalid_builtin, "invalid-builtin")
    HANDLER(invalid_objc_cast, "invalid-objc-cast")
    HANDLER(function_type_mismatch, "function-type-mismatch")
    HANDLER(implicit_conversion, "implicit-conversion")
    HANDLER(nonnull_arg, "nonnull-arg")
    HANDLER(nonnull_return, "nonnull-return")
    HANDLER(nullability_arg, "nullability-arg")
    HANDLER(nullability_return, "nullability-return")
    HANDLER(pointer_overflow, "pointer-overflow")
    HANDLER(cfi_check_fail, "cfi-check-fail")
}
