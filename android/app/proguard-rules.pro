# kotlinx.serialization keeps @Serializable metadata; keep generated serializers.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
-keepclassmembers class com.pedalworkshop.data.** {
    *** Companion;
}
-keepclasseswithmembers class com.pedalworkshop.data.** {
    kotlinx.serialization.KSerializer serializer(...);
}
